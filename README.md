# Mosquitto Admin GUI Stack

Modern Mosquitto management stack composed of an Eclipse Mosquitto broker and a Streamlit-based admin console. The GUI lets you manage users, TLS assets, broker configuration, and reload/restart actions from a browser, while the Mosquitto container responds to trigger files for zero-downtime updates.

## Stack Components

- **`admin-gui`** – Streamlit multipage app served over HTTPS (self-signed by default). Handles authentication, user/TLS/config management, and a built-in MQTT subscriber.
- **`mosquitto`** – Eclipse Mosquitto 2.x image wrapped with a lightweight watcher that reacts to reload/restart trigger files written by the GUI.
- **Compose files** – `docker-compose.dev.yml` builds both services locally; `docker-compose.prod.yml` is ready for prebuilt images (e.g., GHCR).

```
.
├── admin-gui/        # Streamlit application, Dockerfile, entrypoint, pages/
├── mosquitto/        # Mosquitto image wrapper with watcher.sh
├── docker-compose.dev.yml
└── docker-compose.prod.yml
```

## Features

- **Dashboard:** Listener reachability checks, password-file inventory, and recent reload/restart activity.
- **User management:** Add/remove MQTT users across password files, with Mosquitto-compatible PBKDF2 hashing.
- **TLS tooling:** Generate server certificates/keys and optional client-auth roots.
- **Config editor:** Edit `mosquitto.conf` and related files in-place, then trigger reloads.
- **Reload/Restart controls:** Write trigger files that the Mosquitto watcher converts into `SIGHUP` or container restarts.
- **MQTT client:** Browser-based subscriber (paho-mqtt) with auto-refresh, TLS options, and message history.
- **About & housekeeping:** Persistent admin credentials stored under `/admin-gui/config/admin_pwfile`; logout control on every page.

## Prerequisites

- Docker 24+ and Docker Compose V2
- (Optional) Python 3.10+ if you plan to run the Streamlit app directly during development

## Quick Start

### Development (build locally)

```bash
docker compose -f docker-compose.dev.yml up --build
```

- Streams logs to the terminal; use `CTRL+C` to stop.
- Named volumes hold broker data (`mosquitto_data`), logs, config, GUI config, and reload/restart signals.

### Production (consume prebuilt images)

1. Publish images or set registry coordinates via environment variables:
   - `MOSQUITTO_IMAGE` (defaults to `ghcr.io/replace-with-namespace/mosquitto-gui-stack-multipage-mosquitto:latest`)
   - `ADMIN_GUI_IMAGE` (defaults to `ghcr.io/replace-with-namespace/mosquitto-gui-stack-multipage-admin-gui:latest`)
2. Launch in detached mode:

```bash
docker compose -f docker-compose.prod.yml up -d
```

## First-Run Experience

- Browse to `https://localhost:8088` (self-signed certificate).
- The GUI prompts for an admin username/password if `admin_pwfile` is absent. Credentials are stored in Mosquitto's `$7$` PBKDF2-SHA512 format under `/admin-gui/config/admin_pwfile`.
- Configure Mosquitto users/TLS/listeners as needed, then use **Reload Broker** to apply changes without downtime.

## Data & Volumes

| Volume             | Path inside container           | Purpose                                      |
|--------------------|---------------------------------|----------------------------------------------|
| `mosquitto_data`   | `/mosquitto/data`               | Persistent broker data                       |
| `mosquitto_log`    | `/mosquitto/log`                | Broker logs                                  |
| `mosquitto_config` | `/mosquitto/config`             | `mosquitto.conf`, password files, TLS assets |
| `admin_gui_config` | `/admin-gui/config`             | Admin credentials, UI TLS cert/key           |
| `admin_signals`    | `/signals`                      | Reload (`reload`) and restart (`restart`) triggers |

The admin GUI mounts `mosquitto_config` read/write so updates apply immediately, while the Mosquitto container mounts it read-only for safety.

## Key Environment Variables

| Variable               | Default                      | Description                                                  |
|------------------------|------------------------------|--------------------------------------------------------------|
| `ADMIN_CONFIG_DIR`     | `/admin-gui/config`          | Where the GUI stores admin state and UI TLS assets           |
| `MOSQUITTO_CONFIG_DIR` | `/mosquitto/config`          | Base path for broker config, password files, and certs       |
| `SIGNALS_DIR`          | `/signals`                   | Shared directory for reload/restart trigger files            |
| `CERT_DIR`             | `/admin-gui/config`          | (GUI) Directory for generated HTTPS certificate              |
| `CERT_FILE`            | `admin-ui.crt` in `CERT_DIR`  | GUI HTTPS certificate path                                   |
| `KEY_FILE`             | `admin-ui.key` in `CERT_DIR`  | GUI HTTPS private key path                                   |
| `TLS_CN` / `TLS_SAN`   | `Mosquitto Admin` / `DNS:localhost,IP:127.0.0.1` | Controls the self-signed GUI certificate subject & SANs |

Adjust these through Compose `environment` entries or CLI overrides.

## Signals, Reloads, and Restart Flow

- GUI writes `/signals/reload` → watcher removes file and sends `SIGHUP` to Mosquitto (`reload_broker` in the UI).
- GUI writes `/signals/restart` → watcher stops Mosquitto and exits; Docker restarts the container (`restart_broker` in the UI).
- Health check (`pidof mosquitto`) keeps Docker aware of broker liveness.

Ensure the `admin_signals` volume is shared between services; otherwise reload/restart buttons will show errors.

## Local Streamlit Development (outside Docker)

```bash
cd admin-gui
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ADMIN_CONFIG_DIR="$(pwd)/.local-config"
export MOSQUITTO_CONFIG_DIR="/path/to/your/mosquitto/config"
export SIGNALS_DIR="$(pwd)/.signals"
streamlit run "Mosquitto Admin.py"
```

- Create the directories referenced above or point them to your Docker volumes.
- The UI respects hot-reload, so editing files under `pages/` refreshes automatically.

## Building & Publishing Images

```bash
# Mosquitto watcher image
docker build -t your-org/mosquitto-gui-mosquitto:latest mosquitto

# Admin GUI image
docker build -t your-org/mosquitto-gui-admin:latest admin-gui
```

Push to your registry and update the production compose file environment variables accordingly.

## Troubleshooting

- **Cannot log in:** Delete `admin_gui_config` volume to reset admin credentials (you will be prompted to create them again). Do this cautiously in production.
- **Reload/Restart buttons fail:** Verify the `admin_signals` volume exists and both containers mount it at `/signals`.
- **Broker TLS errors:** Ensure generated certs (`server.crt`, `server.key`, CA files) exist under the Mosquitto config volume and that `mosquitto.conf` references them.
- **Self-signed UI certificate warnings:** Replace `admin-ui.crt` and `admin-ui.key` with your own certificate/key pair, or extend `TLS_SAN` to include deployed hostnames before first run.
