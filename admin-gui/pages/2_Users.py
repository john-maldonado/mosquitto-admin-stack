"""
User management page for the Mosquitto admin app.

This page allows administrators to view, add, update, and delete
Mosquitto MQTT users. User credentials are stored in the
Mosquitto password file (`pwfile`) in a PBKDF2‑SHA512 `$7$` format.
"""

import streamlit as st
import common as c

# Enforce authentication
if not c.require_login():
    st.stop()

st.set_page_config(page_title="MQTT Users", page_icon="👥", layout="wide")
st.title("MQTT Users")

# Fetch current users
users = c.read_pw_users()

# Display existing users in a table
st.subheader("Existing users")
if users:
    st.table({"username": users})
else:
    st.info("No users defined yet.")

st.divider()

# Section: Add or update a user
st.subheader("Add / Update User")
col1, col2 = st.columns(2)
with col1:
    username = st.text_input("Username", key="new_username")
with col2:
    password = st.text_input("Password (min 8 chars)", type="password", key="new_password")

if st.button("Save User", key="save_user", disabled=(not username or len(password) < 8)):
    if len(password) < 8:
        st.error("Password must be at least 8 characters.")
    else:
        c.upsert_user(username, password)
        st.success(f"User '{username}' saved.")
        # Immediately refresh to update the user list
        st.rerun()

st.divider()

# Section: Delete a user
st.subheader("Delete User")
if users:
    del_user = st.selectbox("Select user", users, key="delete_user_select")
    if st.button("Delete Selected User", key="delete_user_button"):
        c.delete_user(del_user)
        st.success(f"User '{del_user}' deleted (if existed).")
        st.rerun()
else:
    st.info("No users to delete.")

# Logout button
c.logout_button()