"""
Broker reload page for the Mosquitto admin app.

This page triggers a reload of the Mosquitto broker configuration by
sending the SIGHUP signal to the running mosquitto process. This only
works when the admin container shares a PID namespace with the broker
container (as configured with ``pid: "container:mosquitto"`` in the
docker-compose file). If the process cannot be found, a helpful
message is displayed.
"""

import streamlit as st
import common as c

if not c.require_login():
    st.stop()

st.set_page_config(page_title="Reload Broker", page_icon="♻️", layout="wide")
st.title("Reload Mosquitto Broker")

st.write(
    "Use **Reload** to re-read the configuration without a full restart (via SIGHUP or trigger file). "
    "Use **Restart** to gracefully stop the broker and rely on Docker to restart it (via trigger file). "
    "Ensure that the signals directory is mounted and the mosquitto watcher is running."
)

col1, col2 = st.columns(2)
with col1:
    if st.button("Reload broker", key="reload_btn", use_container_width=True):
        ok, msg = c.reload_broker()
        (st.success if ok else st.error)(msg)
with col2:
    if st.button("Restart broker", key="restart_btn", use_container_width=True):
        ok, msg = c.restart_broker()
        (st.success if ok else st.error)(msg)

# Logout button
c.logout_button()