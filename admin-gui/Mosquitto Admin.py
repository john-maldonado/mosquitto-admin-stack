"""
Main entry point for the Mosquitto admin GUI Streamlit application.

This Home page shows a grid of tiled cards that link to commonly used
sections (Users, TLS, Config Editor, Reload/Restart, etc.). Pages live
under the `pages/` directory and are still reachable via the sidebar.
"""

import os
import time
import streamlit as st
import common as c

# ------------------------------- Auth ----------------------------------------
if not c.require_login():
    st.stop()

# --------------------------- Page config/title -------------------------------
st.set_page_config(page_title="Mosquitto Admin", layout="wide")
st.title("Mosquitto Admin")

st.caption(
    "Quickly jump to common tasks below. You can also use the sidebar to browse all pages."
)

# ------------------------------ Card helper ----------------------------------
def card(label: str, description: str, target_page: str, *, key: str):
    """
    Render a simple 'card' with a title, short description, and a link button
    that navigates to a Streamlit page file in /pages (via st.page_link).
    """
    with st.container(border=True):
        st.markdown(f"### {label}")
        if description:
            st.write(description)
        # st.page_link is available in recent Streamlit versions.
        # If you’re on an older version, fall back to st.write with instructions.
        try:
            st.page_link(target_page, label=f"Open {label}", use_container_width=True)
        except Exception:
            st.write(f"Open **{label}** from the sidebar.")

# ------------------------------ Cards grid -----------------------------------
# Adjust the order to taste. You mentioned Dashboard still exists, so include it.
tiles = [
    {
        "label": "Dashboard",
        "desc": "Overview and quick stats for your broker and configuration.",
        "page": "pages/1_Dashboard.py",
        "key": "dash",
    },
    {
        "label": "Users",
        "desc": "Add, update, or remove MQTT users in the password file.",
        "page": "pages/2_Users.py",
        "key": "users",
    },
    {
        "label": "Server TLS",
        "desc": "Generate a self-signed CA and server certificate/key for TLS listeners.",
        "page": "pages/3_Server_TLS.py",
        "key": "srv_tls",
    },
    {
        "label": "Client TLS",
        "desc": "Optionally create a client CA for mutual-TLS client authentication.",
        "page": "pages/4_Client_TLS.py",
        "key": "cli_tls",
    },
    {
        "label": "Config Editor",
        "desc": "Edit `mosquitto.conf` and related files. Save to apply via Reload or Restart.",
        "page": "pages/5_Config_Editor.py",
        "key": "config",
    },
    {
        "label": "Reload / Restart",
        "desc": "Reload config (SIGHUP) or request a clean restart via trigger files.",
        "page": "pages/6_Reload_Broker.py",
        "key": "reload",
    },
    {
        "label": "About",
        "desc": "Version info and notes about this admin utility.",
        "page": "pages/7_About.py",
        "key": "about",
    },
]

# Render in a responsive 3-column grid
cols_per_row = 3
for i in range(0, len(tiles), cols_per_row):
    row = tiles[i : i + cols_per_row]
    cols = st.columns(len(row))
    for col, t in zip(cols, row):
        with col:
            card(t["label"], t["desc"], t["page"], key=t["key"])

st.divider()

# --------------------------- Optional footer bits ----------------------------
# Quick presence checks (nice lightweight status at the bottom)
cfg_dir = c.MOSQUITTO_CONFIG_DIR
sig_dir = getattr(c, "SIGNALS_DIR", "/signals")
st.caption("Paths")
cc1, cc2 = st.columns(2)
with cc1:
    st.code(cfg_dir)
with cc2:
    st.code(sig_dir)

# Logout button on Home as well
c.logout_button()
