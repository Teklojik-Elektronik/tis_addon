#!/usr/bin/env bash
set -e

CONFIG_PATH=/data/options.json

# Read configuration from options.json
GATEWAY_IP=$(jq --raw-output '.gateway_ip // ""' $CONFIG_PATH)
UDP_PORT=$(jq --raw-output '.udp_port // "6000"' $CONFIG_PATH)

# Check if gateway IP is configured
if [ -z "$GATEWAY_IP" ]; then
    echo "[WARNING] Gateway IP not configured in addon settings!"
    echo "[INFO] You can configure it from Web UI or addon Configuration tab"
    GATEWAY_IP="0.0.0.0"
fi

echo "[INFO] Starting TIS Control Web UI..."
echo "[INFO] Gateway IP: ${GATEWAY_IP}"
echo "[INFO] UDP Port: ${UDP_PORT}"

# Change to app directory
cd /app

# Start web server
exec python3 web_ui.py --gateway "${GATEWAY_IP}" --port "${UDP_PORT}"
