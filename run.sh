#!/usr/bin/env bash
set -e

CONFIG_PATH=/data/options.json

# Read configuration from options.json
GATEWAY_IP=$(jq --raw-output '.gateway_ip // "192.168.1.200"' $CONFIG_PATH)
UDP_PORT=$(jq --raw-output '.udp_port // "6000"' $CONFIG_PATH)

echo "[INFO] Starting TIS Control Web UI..."
echo "[INFO] Gateway IP: ${GATEWAY_IP}"
echo "[INFO] UDP Port: ${UDP_PORT}"

# Change to app directory
cd /app

# Start web server
exec python3 web_ui.py --gateway "${GATEWAY_IP}" --port "${UDP_PORT}"
