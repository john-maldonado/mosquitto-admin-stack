"""
About page for the Mosquitto admin app.

Updated to reflect the signal-file watcher architecture (no PID sharing),
reload vs restart behavior, and current file/volume layout.
"""

import streamlit as st
import common as c

# Require authentication before showing the page
if not c.require_login():
    st.stop()

st.set_page_config(page_title="About", page_icon="ℹ️", layout="wide")
st.title("About this Admin UI")

st.markdown(
    """
    ## Overview
    This Streamlit application provides a simple, file-backed admin UI for an
    Eclipse Mosquitto broker. It focuses on:
    - Local, file-based **admin authentication** (no external DB).
    - Managing MQTT **users** (Mosquitto `pwfile`).
    - Generating **server TLS** credentials and optionally a **client CA**.
    - Editing `mosquitto.conf` directly in the browser.
    - Applying changes via **Reload** (SIGHUP) or **Restart** (SIGTERM) using a
      signal-file **watcher** in the Mosquitto container (no PID namespace sharing).

    ---
    ## Architecture (what’s running now)
    **Admin container (Streamlit)**
    - Renders the UI and writes config/artifacts to the mounted Mosquitto config dir.
    - Requests broker actions by creating trigger files in a shared signals directory.

    **Mosquitto container (custom image)**
    - Starts `mosquitto` and a tiny **watcher** loop.
    - The watcher monitors the shared **signals** directory:
      - `/signals/reload` → sends `SIGHUP` to Mosquitto (reload config).
      - `/signals/restart` → sends `SIGTERM`, waits, then exits so Docker restarts it.

    This design **decouples lifecycles**: the admin stays up while the broker
    reloads/restarts—no `pid: "container:mosquitto"` required.

    ---
    ## Reload vs Restart
    - **Reload** (SIGHUP): Re-reads configuration and certain files.  
      Not all changes can be applied (e.g., adding/removing **listeners** typically
      requires a restart).
    - **Restart** (SIGTERM): Graceful stop; Docker brings the broker back up.  
      Use this after changes that require re-binding ports/listeners or re-initializing TLS.

    The UI first tries a direct SIGHUP if a Mosquitto PID is visible; otherwise it
    falls back to writing the trigger file. Restart is requested via trigger file.

    ---
    ## Paths & files
    These paths are derived from the environment and mounts used by the stack:

    """
)

# Show key paths dynamically so the page reflects the running config
st.code(
    f"""MOSQUITTO_CONFIG_DIR = {c.MOSQUITTO_CONFIG_DIR}
SIGNALS_DIR          = {getattr(c, "SIGNALS_DIR", "/signals")}
MOSQCONF             = {c.MOSQCONF}
PWFILE               = {c.PWFILE}
ACLFILE              = {c.ACLFILE}
CAFILE               = {c.CAFILE}
CERTFILE             = {c.CERTFILE}
KEYFILE              = {c.KEYFILE}
CLIENT_CAFILE        = {c.CLIENT_CAFILE}
ADMIN_PWFILE         = {c.ADMIN_PWFILE if hasattr(c, "ADMIN_PWFILE") else "<admin_pwfile>"}""",
    language="bash",
)

st.markdown(
    """
    **Where things live**
    - **Admin credentials** (UI login): stored in a file within `ADMIN_CONFIG_DIR`
      as `$7$` PBKDF2-SHA512 (Mosquitto-compatible).
    - **MQTT users**: stored in `PWFILE` with `$7$` hashes; updated in-place.
    - **TLS artifacts**: written under `MOSQUITTO_CONFIG_DIR` (server CA, server cert/key,
      optional client CA).
    - **Signals**: files created in `SIGNALS_DIR` instruct the watcher to Reload/Restart.

    ---
    ## Security model
    - The UI is protected by local file-based auth. Keep the admin config volume private.
    - Passwords for MQTT users and the admin are stored as **PBKDF2-SHA512 `$7$`** hashes.
    - The admin container needs **write access** to the Mosquitto config volume and the
      shared signals volume.
    - No Docker socket access is required for normal operations.

    ---
    ## Troubleshooting quick tips
    - **Reload doesn’t seem to apply changes**  
      Some directives (e.g., listener add/remove) require a **Restart**.
    - **No action when pressing Reload/Restart**  
      Verify the shared signals directory is mounted in **both** containers and writable
      by the admin.
    - **Broker won’t start after changes**  
      Check `mosquitto.conf` syntax; fall back to the default template if needed.

    ---
    ## Acknowledgements
    - Built with [Streamlit](https://streamlit.io/).
    - TLS implemented with [cryptography](https://cryptography.io/).
    - Broker powered by [Eclipse Mosquitto](https://mosquitto.org/).
    """
)

# Logout button
st.divider()
c.logout_button()