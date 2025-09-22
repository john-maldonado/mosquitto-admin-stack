"""
Server TLS page for the Mosquitto admin app.

This page allows administrators to generate a self-signed server CA and
server certificate/key for the broker, upload/replace existing TLS
artifacts, download or view artifacts (except private key), and see
the current TLS state.
"""

import os
import time
import streamlit as st
import common as c

# ----------------------------- auth -------------------------------------------
if not c.require_login():
    st.stop()

st.set_page_config(page_title="Server TLS", page_icon="🔐", layout="wide")
c.set_active_page("server_tls")
st.title("Server TLS (broker identity)")

# ----------------------------- helpers ----------------------------------------
def _mtime(path: str) -> str | None:
    try:
        ts = os.path.getmtime(path)
        return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts))
    except Exception:
        return None

def _filesize(path: str) -> str | None:
    try:
        size = os.path.getsize(path)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.0f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    except Exception:
        return None

def _is_pem_cert(text: str) -> bool:
    t = text.strip()
    return "-----BEGIN CERTIFICATE-----" in t and "-----END CERTIFICATE-----" in t

def _is_pem_key(text: str) -> bool:
    t = text.strip()
    # Accept common key headers (PKCS#1, PKCS#8, EC):
    return any(
        h in t
        for h in [
            "-----BEGIN PRIVATE KEY-----",
            "-----BEGIN RSA PRIVATE KEY-----",
            "-----BEGIN EC PRIVATE KEY-----",
        ]
    )

def _safe_write(path: str, data: bytes, mode: int | None = None) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)
    if mode is not None:
        try:
            os.chmod(path, mode)
        except Exception:
            pass

def render_artifact_card(
    title: str,
    path: str,
    download_name: str | None = None,
    *,
    language: str = "pem",
    expose_content: bool = True,
    warn: str | None = None,
):
    """
    Render a file card with metadata, optional download, and optional viewer.

    expose_content=False disables both download and viewer for the artifact.
    """
    with st.container(border=True):
        st.subheader(title, anchor=False)

        exists = os.path.exists(path)
        status = "present ✅" if exists else "missing ❌"

        meta_col, action_col = st.columns([3, 2], gap="large")
        with meta_col:
            st.write(f"**Path:** `{path}`")
            st.write(f"**Status:** {status}")
            if exists:
                mt = _mtime(path)
                sz = _filesize(path)
                details = [s for s in [f"modified: {mt}" if mt else None, f"size: {sz}" if sz else None] if s]
                if details:
                    st.caption(" • ".join(details))

        with action_col:
            if exists and expose_content and download_name:
                try:
                    with open(path, "rb") as f:
                        st.download_button(
                            label=f"Download {title}",
                            data=f.read(),
                            file_name=download_name,
                            use_container_width=True,
                            key=f"dl_{title.replace(' ','_').lower()}"
                        )
                except Exception as e:
                    st.error(f"Download unavailable: {e}")
            else:
                st.button(f"Download {title}", disabled=True, use_container_width=True)

            if warn:
                st.caption(f"⚠️ {warn}")

        # Optional viewer
        if exists and expose_content:
            with st.expander(f"View {title}", expanded=False):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        st.code(f.read(), language=language)
                except Exception as e:
                    st.error(f"Could not read file: {e}")
        elif not expose_content:
            st.info(f"{title}: viewing and download disabled for security.")

        if not exists:
            st.info(f"{title} file not found.")

# ----------------------------- quick status -----------------------------------
col1, col2, col3 = st.columns(3)
col1.write(f"**Server CA:** {'present' if os.path.exists(c.CAFILE) else 'missing'}")
col2.write(f"**Server Certificate:** {'present' if os.path.exists(c.CERTFILE) else 'missing'}")
col3.write(f"**Server Key:** {'present' if os.path.exists(c.KEYFILE) else 'missing'}")

st.divider()

# ----------------------------- generate form ----------------------------------
st.subheader("Generate self-signed Server CA and Certificate")
cn = st.text_input("Common Name (CN)", value="mosquitto.local", key="srv_cn")
alt = st.text_input(
    "Subject Alternative Names (comma-separated DNS or IP)",
    value="localhost,127.0.0.1",
    key="srv_alt"
)
days = st.number_input("Validity (days)", min_value=1, max_value=3650, value=825, step=1, key="srv_days")

if st.button("Generate Server TLS", key="srv_generate", use_container_width=True):
    try:
        alt_hosts = [s.strip() for s in alt.split(",") if s.strip()]
        c.gen_server_ca_and_cert(cn, alt_hosts, int(days))
        st.success("Generated server CA, key, and certificate.")
    except Exception as e:
        st.error(f"Generation failed: {e}")

st.divider()

# ----------------------------- uploads ----------------------------------------
st.subheader("Upload / Replace Artifacts")

up_ca, up_cert, up_key = st.columns(3, gap="large")

with up_ca:
    st.caption("Upload **Server CA** (PEM certificate)")
    f = st.file_uploader("Choose CA", type=["crt", "pem", "cer"], key="up_srv_ca")
    if f and st.button("Upload CA", key="btn_up_srv_ca", use_container_width=True):
        try:
            text = f.read().decode("utf-8", errors="ignore")
            if not _is_pem_cert(text):
                st.error("Uploaded file does not look like a PEM certificate.")
            else:
                _safe_write(c.CAFILE, text.encode("utf-8"), mode=0o644)
                st.success("Server CA uploaded.")
                st.rerun()
        except Exception as e:
            st.error(f"Upload failed: {e}")

with up_cert:
    st.caption("Upload **Server Certificate** (PEM certificate)")
    f = st.file_uploader("Choose cert", type=["crt", "pem", "cer"], key="up_srv_cert")
    if f and st.button("Upload Cert", key="btn_up_srv_cert", use_container_width=True):
        try:
            text = f.read().decode("utf-8", errors="ignore")
            if not _is_pem_cert(text):
                st.error("Uploaded file does not look like a PEM certificate.")
            else:
                _safe_write(c.CERTFILE, text.encode("utf-8"), mode=0o644)
                st.success("Server certificate uploaded.")
                st.rerun()
        except Exception as e:
            st.error(f"Upload failed: {e}")

with up_key:
    st.caption("Upload **Server Private Key** (PEM key)")
    f = st.file_uploader("Choose key", type=["key", "pem"], key="up_srv_key")
    if f and st.button("Upload Key", key="btn_up_srv_key", use_container_width=True):
        try:
            text = f.read().decode("utf-8", errors="ignore")
            if not _is_pem_key(text):
                st.error("Uploaded file does not look like a PEM private key.")
            else:
                _safe_write(c.KEYFILE, text.encode("utf-8"), mode=0o600)
                st.success("Server private key uploaded.")
                st.rerun()
        except Exception as e:
            st.error(f"Upload failed: {e}")

st.divider()

# ----------------------------- artifact cards (stacked) ------------------------
st.subheader("Artifacts")

render_artifact_card(
    title="Server CA",
    path=c.CAFILE,
    download_name="ca-root-cert.crt",
    language="pem",
    expose_content=True
)

render_artifact_card(
    title="Server Certificate",
    path=c.CERTFILE,
    download_name="server.crt",
    language="pem",
    expose_content=True
)

render_artifact_card(
    title="Server Private Key",
    path=c.KEYFILE,
    download_name=None,          # never distributed via UI
    language="pem",
    expose_content=False,        # 🚫 no view or download
    warn="Private keys should not be exposed."
)

st.divider()
c.logout_button()
