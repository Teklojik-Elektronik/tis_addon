#!/usr/bin/env bash
set -e

CONFIG_PATH=/data/options.json

# Read configuration from options.json
LOG_LEVEL=$(jq --raw-output '.log_level // "info"' $CONFIG_PATH)

echo "[INFO] Starting TIS Control Web UI..."
echo "[INFO] Log Level: ${LOG_LEVEL}"
echo "[INFO] Device discovery via TIS integration API"

# Check for Supervisor token
if [ -n "$SUPERVISOR_TOKEN" ]; then
    echo "[INFO] Supervisor token detected - Auto-reload enabled"
else
    echo "[WARNING] No supervisor token - Auto-reload disabled"
fi

# Change to app directory
cd /app

# Start web server (no gateway/port params needed)
exec python3 web_ui.py --log-level "${LOG_LEVEL}"
