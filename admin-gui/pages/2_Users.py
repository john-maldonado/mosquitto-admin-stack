"""
User management page for the Mosquitto admin app.

This page allows administrators to view, add, update, and delete
Mosquitto MQTT users. User credentials are stored in Mosquitto
password files (default `pwfile` or files under `passwd_files/`)
in a PBKDF2‑SHA512 `$7$` format.
"""

import streamlit as st
import common as c

# Enforce authentication
if not c.require_login():
    st.stop()

st.set_page_config(page_title="MQTT Users", page_icon="👥", layout="wide")
c.set_active_page("users")
st.title("MQTT Users")
st.caption(
    "Manage Mosquitto password files and the MQTT accounts stored in them. "
    "Each listener in mosquitto.conf can reference a different file under "
    "`/mosquitto/config/passwd_files`."
)

pending_select_key = "password_file_select_pending"
pending_value = st.session_state.pop(pending_select_key, None)
if pending_value is not None:
    st.session_state["password_file_select"] = pending_value

files = c.discover_password_files()
if not files:
    st.warning(
        "No password files discovered. Create one below to get started.")
    selected_entry = None
    options = []
else:
    options = [entry.path for entry in files]
    labels = {entry.path: entry.label for entry in files}
    default_path = st.session_state.get("password_file_select")
    if default_path not in options:
        default_path = options[0]
    selected_path = st.selectbox(
        "Password file",
        options,
        key="password_file_select",
        index=options.index(default_path) if default_path in options else 0,
        format_func=lambda p: labels.get(p, p),
    ) if options else None
    selected_entry = next((entry for entry in files if entry.path == selected_path), None)

with st.expander("Create new password file", expanded=not files):
    new_name = st.text_input(
        "File name",
        key="new_pwfile_name",
        help="Stored under passwd_files/. Use letters, numbers, dot, dash, or underscore.",
    )
    create_disabled = not new_name.strip()
    if st.button("Create password file", key="create_pwfile_btn", disabled=create_disabled):
        try:
            created_path = c.create_password_file(new_name)
        except ValueError as exc:
            st.error(str(exc))
        except FileExistsError:
            st.error("A password file with that name already exists.")
        except Exception as exc:
            st.error(f"Could not create password file: {exc}")
        else:
            st.success(f"Created password file at {created_path}.")
            st.session_state[pending_select_key] = created_path
            st.session_state["new_pwfile_name"] = ""
            st.rerun()

if not selected_entry:
    st.stop()

with st.container(border=True):
    st.subheader(f"Details — {selected_entry.label}")
    st.code(selected_entry.path, language=None)
    meta_cols = st.columns(3)
    meta_cols[0].metric("Users", selected_entry.user_count)
    meta_cols[1].metric("Exists", "yes" if selected_entry.exists else "no")
    size_value = f"{selected_entry.size_bytes} B" if selected_entry.size_bytes is not None else "—"
    meta_cols[2].metric("Size", size_value)
    if selected_entry.modified:
        st.caption(selected_entry.modified.strftime("Last modified: %Y-%m-%d %H:%M:%S UTC"))

st.subheader("Existing users")
if selected_entry.usernames:
    st.table({"username": selected_entry.usernames})
else:
    st.info("No users defined in this password file yet.")

st.divider()

# Section: Add or update a user
st.subheader("Add / Update User")
col1, col2 = st.columns(2)
with col1:
    username = st.text_input("Username", key="new_username")
with col2:
    password = st.text_input("Password (min 8 chars)", type="password", key="new_password")

save_disabled = not username or len(password) < 8
if st.button("Save User", key="save_user", disabled=save_disabled):
    if len(password) < 8:
        st.error("Password must be at least 8 characters.")
    else:
        c.upsert_user(username, password, path=selected_entry.path)
        st.success(f"User '{username}' saved to {selected_entry.label}.")
        st.rerun()

st.divider()

# Section: Delete a user
st.subheader("Delete User")
if selected_entry.usernames:
    del_user = st.selectbox("Select user", selected_entry.usernames, key="delete_user_select")
    if st.button("Delete Selected User", key="delete_user_button"):
        c.delete_user(del_user, path=selected_entry.path)
        st.success(f"User '{del_user}' deleted (if existed) from {selected_entry.label}.")
        st.rerun()
else:
    st.info("No users to delete in this password file.")

# Logout button
c.logout_button()
