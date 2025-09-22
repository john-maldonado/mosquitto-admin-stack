"""
Client TLS page for the Mosquitto admin app.

This page lets administrators manage the Certificate Authority (CA)
used to verify client certificates. When the broker is configured with
`require_certificate true` on a TLS listener, it will only accept
connections from clients presenting certificates signed by the CA
stored here (see `common.CLIENT_CAFILE`).
"""

import os
import time
import streamlit as st
import common as c

# ----------------------------- auth -------------------------------------------
if not c.require_login():
    st.stop()

st.set_page_config(page_title="Client TLS", page_icon="🔏", layout="wide")
c.set_active_page("client_tls")
st.title("Client TLS (client authentication)")

st.write(
    "Upload a Certificate Authority (CA) to verify client certificates. "
    "When Mosquitto is configured with `require_certificate true`, only "
    "clients presenting certificates signed by this CA will be allowed to connect."
)

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
            st.info(f"{title}: viewing and download disabled.")

        if not exists:
            st.info(f"{title} file not found.")

# ----------------------------- current status ---------------------------------
st.subheader("Current client CA status")
if os.path.exists(c.CLIENT_CAFILE):
    st.success("Client CA is present.")
else:
    st.warning("Client CA is missing.")

st.divider()

# ----------------------------- upload form ------------------------------------
st.subheader("Upload client CA")
uploaded = st.file_uploader(
    "Select a PEM-encoded certificate",
    type=["crt", "pem", "cer"],
    key="client_ca_upload"
)

col_up1, col_up2 = st.columns([1, 3])
with col_up1:
    if uploaded is not None and st.button("Upload Client CA", key="client_ca_upload_btn", use_container_width=True):
        try:
            os.makedirs(os.path.dirname(c.CLIENT_CAFILE), exist_ok=True)
            data = uploaded.read()
            with open(c.CLIENT_CAFILE, "wb") as f:
                f.write(data)
            # best-effort restrict perms
            try:
                os.chmod(c.CLIENT_CAFILE, 0o644)
            except Exception:
                pass
            st.success("Client CA uploaded successfully.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save client CA: {e}")
with col_up2:
    st.caption("Accepted types: .crt, .pem, .cer. File is stored at the configured `CLIENT_CAFILE` path.")

st.divider()

# ----------------------------- artifact card ----------------------------------
st.subheader("Artifact")
render_artifact_card(
    title="Client CA",
    path=c.CLIENT_CAFILE,
    download_name="client-ca.crt",
    language="pem",
    expose_content=True
)

st.divider()
c.logout_button()
