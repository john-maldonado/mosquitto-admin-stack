"""
Configuration editor page for the Mosquitto admin app.

This page provides a simple text editor for the broker's
``mosquitto.conf`` file. Administrators can view and modify the
configuration, or load a fresh default template provided by the GUI.
Changes are written to disk when the **Save** button is pressed. To
apply changes, use the Reload Broker page or restart the Mosquitto
service.
"""

import streamlit as st
import common as c

# Require login before proceeding
if not c.require_login():
    st.stop()

st.set_page_config(page_title="Config Editor", page_icon="📝", layout="wide")
c.set_active_page("config_editor")
st.title("Mosquitto Configuration Editor")

# Initialize the text buffer in session state on first load
buffer_key = "conf_editor_buffer"
if buffer_key not in st.session_state:
    # Load existing config or default
    st.session_state[buffer_key] = c.read_text_or(c.MOSQCONF, c.DEFAULT_CONF)

st.markdown(
    "Edit the broker configuration below. This editor writes to "
    f"`{c.MOSQCONF}`. When you're finished, click **Save** to persist "
    "your changes. Reload the broker afterwards to apply the new settings."
)

# Text area for editing the configuration
content = st.text_area(
    "mosquitto.conf", value=st.session_state[buffer_key], height=420, key="conf_editor_area"
)

# Buttons for saving and loading default
col_save, col_default = st.columns(2)
with col_save:
    if st.button("Save", key="conf_save_btn"):
        try:
            c.write_text(c.MOSQCONF, content)
            st.session_state[buffer_key] = content
            st.success("Configuration saved. Reload the broker to apply changes.")
        except Exception as e:
            st.error(f"Failed to save configuration: {e}")
with col_default:
    if st.button("Load default template", key="conf_default_btn"):
        st.session_state[buffer_key] = c.DEFAULT_CONF
        st.rerun()

# Logout button
c.logout_button()
