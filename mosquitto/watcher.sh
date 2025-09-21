#!/bin/sh
set -eu

# Start mosquitto in the background
mosquitto -c /mosquitto/config/mosquitto.conf &
MOSQ_PID=$!
echo "Watcher started mosquitto with PID $MOSQ_PID"

# Loop forever watching for trigger files
while :; do
    # Reload trigger
    if [ -f /signals/reload ]; then
        echo "Watcher: reload trigger detected"
        rm -f /signals/reload || true
        kill -HUP "$MOSQ_PID" || true
    fi

    # Restart trigger
    if [ -f /signals/restart ]; then
        echo "Watcher: restart trigger detected"
        rm -f /signals/restart || true
        kill -TERM "$MOSQ_PID" || true
        wait "$MOSQ_PID" || true
        echo "Watcher exiting so the container will restart"
        exit 0
    fi

    sleep 1
done
