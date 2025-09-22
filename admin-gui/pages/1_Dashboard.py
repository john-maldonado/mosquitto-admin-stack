"""
Dashboard page for the Mosquitto admin Streamlit app.

Shows high-level broker status without PID sharing or Docker API:
- TCP reachability for 1883 (plain) and 8883 (TLS)
- Last reload/restart trigger timestamps from the shared signals dir
- Per-listener cards (Auth & TLS) parsed from mosquitto.conf
- Presence and timestamps for key files
"""

import os
import time
import socket
import ssl
import hashlib
from typing import Optional, Tuple, List

import streamlit as st
import common as c

# ------------------------------ Auth -----------------------------------------
if not c.require_login():
    st.stop()

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
c.set_active_page("dashboard")
st.title("Dashboard")

# ------------------------------ Helpers --------------------------------------
def _exists(p: str) -> bool:
    try:
        return os.path.exists(p)
    except Exception:
        return False

def _mtime_str(p: str) -> Optional[str]:
    try:
        ts = os.path.getmtime(p)
        return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts))
    except Exception:
        return None

def tcp_check(host: str, port: int, timeout: float = 1.5) -> Tuple[bool, Optional[str]]:
    """Return (ok, err) testing a plain TCP connect."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, None
    except Exception as e:
        return False, str(e)

def tls_check(host: str, port: int, timeout: float = 2.0) -> Tuple[bool, Optional[str]]:
    """
    Attempt a minimal TLS handshake (no cert validation) to confirm listener is alive.
    Returns (ok, err).
    """
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as _ssock:
                return True, None
    except Exception as e:
        return False, str(e)

def sha256_file(path: str) -> Optional[str]:
    if not _exists(path):
        return None
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

# ------------------------------ Metrics row ----------------------------------
password_files = c.discover_password_files()
total_users = sum(entry.user_count for entry in password_files)
sig_dir = getattr(c, "SIGNALS_DIR", "/signals")
reload_ts = _mtime_str(os.path.join(sig_dir, "reload"))
restart_ts = _mtime_str(os.path.join(sig_dir, "restart"))

# Try reachability to the broker by service name inside the default Compose network
mqtt_ok, mqtt_err = tcp_check("mosquitto", 1883)
tls_ok, tls_err   = tls_check("mosquitto", 8883)

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Users", total_users)
col2.metric("MQTT 1883", "up" if mqtt_ok else "down")
col3.metric("MQTT TLS 8883", "up" if tls_ok else "down")
col4.metric("Server CA", "present" if _exists(c.CAFILE) else "missing")
col5.metric("Server Cert", "present" if _exists(c.CERTFILE) else "missing")
col6.metric("Server Key", "present" if _exists(c.KEYFILE) else "missing")

if not mqtt_ok or not tls_ok:
    with st.expander("Connection diagnostics", expanded=False):
        if not mqtt_ok:
            st.write(f"1883 error: {mqtt_err}")
        if not tls_ok:
            st.write(f"8883 error: {tls_err}")

if password_files:
    st.subheader("Password files")
    table_rows = []
    for entry in password_files:
        table_rows.append(
            {
                "label": entry.label,
                "path": entry.path,
                "users": entry.user_count,
                "exists": "yes" if entry.exists else "no",
                "size_bytes": entry.size_bytes if entry.size_bytes is not None else "",
                "modified_utc": entry.modified.strftime("%Y-%m-%d %H:%M:%S") if entry.modified else "",
            }
        )
    st.dataframe(table_rows, use_container_width=True)

# ------------------------- Signals / recent actions --------------------------
st.subheader("Recent triggers")
rc1, rc2 = st.columns(2)
with rc1:
    st.write("Last reload trigger")
    st.write(reload_ts or "None")
with rc2:
    st.write("Last restart trigger")
    st.write(restart_ts or "None")

st.divider()

# -------------------------- Configuration highlights (cards) -----------------
st.subheader("Configuration highlights")

listeners, meta = c.parse_mosquitto_conf_listeners()
if not listeners:
    st.info("No explicit 'listener' directives found in mosquitto.conf (defaults may apply).")
else:
    st.caption(
        "Each card shows the effective settings for a listener. "
        f"per_listener_settings = {'true' if meta.get('per_listener_settings') else 'false'}"
    )

    def _bool_str(v):
        if v is None:
            return "not set"
        return "true" if bool(v) else "false"

    def _path_with_status(p: Optional[str]) -> str:
        if not p:
            return "not set"
        return f"{p} ({'exists' if _exists(p) else 'missing'})"

    for lst in listeners:
        port = lst["port"]
        addr = lst.get("address") or "0.0.0.0"
        auth = lst["auth"]
        tls  = lst["tls"]

        with st.container(border=True):
            st.markdown(f"**listener {port} {addr}**")

            colA, colB = st.columns(2)

            # ---- Auth / Anonymous
            with colA:
                st.write("Auth / Anonymous")
                st.write(f"allow_anonymous: {_bool_str(auth.get('allow_anonymous'))}")

                st.write("password_file:")
                st.code(_path_with_status(auth.get("password_file")), language=None)

                if auth.get("acl_file"):
                    st.write("acl_file:")
                    st.code(_path_with_status(auth.get("acl_file")), language=None)

            # ---- TLS
            with colB:
                st.write("TLS")
                enabled = any(tls.get(k) for k in ("cafile", "capath", "certfile", "keyfile"))
                st.write(f"enabled: {'yes' if enabled else 'no'}")

                if tls.get("cafile"):
                    st.write("cafile")
                    st.code(_path_with_status(tls.get("cafile")), language=None)
                if tls.get("capath"):
                    st.write("capath")
                    st.code(_path_with_status(tls.get("capath")), language=None)
                if tls.get("certfile"):
                    st.write("certfile")
                    st.code(_path_with_status(tls.get("certfile")), language=None)
                if tls.get("keyfile"):
                    st.write("keyfile")
                    st.code(_path_with_status(tls.get("keyfile")), language=None)

                if "require_certificate" in tls:
                    st.write(f"require_certificate: {_bool_str(tls.get('require_certificate'))}")
                if "use_identity_as_username" in tls:
                    st.write(f"use_identity_as_username: {_bool_str(tls.get('use_identity_as_username'))}")
                if tls.get("crlfile"):
                    st.write("crlfile")
                    st.code(_path_with_status(tls.get("crlfile")), language=None)
                if tls.get("tls_version"):
                    st.write(f"tls_version: {tls.get('tls_version')}")
                if tls.get("ciphers"):
                    st.write(f"ciphers: {tls.get('ciphers')}")

# --------------------------- Files overview ----------------------------------
st.subheader("Files & timestamps")

paths = [
    ("CONFIG_DIR", c.MOSQUITTO_CONFIG_DIR),
    ("MOSQCONF", c.MOSQCONF),
    ("PWFILE", c.PWFILE),
    ("PASSWD_FILES_DIR", c.PASSWD_FILES_DIR),
    ("ACLFILE", c.ACLFILE),
    ("CAFILE", c.CAFILE),
    ("CERTFILE", c.CERTFILE),
    ("KEYFILE", c.KEYFILE),
    ("CLIENT_CAFILE", c.CLIENT_CAFILE),
    ("SIGNALS_DIR", sig_dir),
]

pcol1, pcol2 = st.columns(2)
for i, (label, path) in enumerate(paths):
    with (pcol1 if i % 2 == 0 else pcol2):
        status = "present" if _exists(path) else "missing"
        mt = _mtime_str(path)
        st.write(f"**{label}** — {status}")
        st.code(path, language=None)
        if mt:
            st.caption(f"modified: {mt}")

# ------------------------ Config hash (drift aid) ----------------------------
st.subheader("Config hash")
conf_hash = sha256_file(c.MOSQCONF)
if conf_hash:
    st.code(conf_hash)
else:
    st.write("Config file not found.")

# ------------------------------- Logout --------------------------------------
st.divider()
c.logout_button()
