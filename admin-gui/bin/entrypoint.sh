#!/usr/bin/env bash
set -euo pipefail

CERT_DIR="${CERT_DIR:-/admin-gui/config}"
CERT_FILE="${CERT_FILE:-$CERT_DIR/admin-ui.crt}"
KEY_FILE="${KEY_FILE:-$CERT_DIR/admin-ui.key}"
TLS_CN="${TLS_CN:-Mosquitto Admin}"
TLS_DAYS="${TLS_DAYS:-825}"
# Add your domain(s)/IPs as needed:
TLS_SAN="${TLS_SAN:-DNS:localhost,IP:127.0.0.1}"

mkdir -p "$CERT_DIR"

if [[ ! -s "$CERT_FILE" || ! -s "$KEY_FILE" ]]; then
  echo "[entrypoint] Generating self-signed cert in $CERT_DIR ..."
  TMP_OPENSSL_CONF="$(mktemp)"
  cat > "$TMP_OPENSSL_CONF" <<EOF
[req]
default_bits       = 2048
default_md         = sha256
prompt             = no
encrypt_key        = no
distinguished_name = dn
x509_extensions    = v3_req

[dn]
CN = ${TLS_CN}

[v3_req]
subjectAltName = ${TLS_SAN}
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
EOF

  openssl req -x509 -nodes -days "$TLS_DAYS" \
    -newkey rsa:2048 \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -config "$TMP_OPENSSL_CONF"

  rm -f "$TMP_OPENSSL_CONF"
  chmod 600 "$KEY_FILE"
  echo "[entrypoint] Self-signed cert generated."
else
  echo "[entrypoint] Using existing cert: $CERT_FILE"
fi

# Hand off to Streamlit (config.toml contains all server settings)
exec streamlit run "Mosquitto Admin.py"