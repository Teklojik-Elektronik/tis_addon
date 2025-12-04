#!/usr/bin/env bashio

# Get configuration from Home Assistant
GATEWAY_IP=$(bashio::config 'gateway_ip')
UDP_PORT=$(bashio::config 'udp_port')

bashio::log.info "Starting TIS Control Web UI..."
bashio::log.info "Gateway IP: ${GATEWAY_IP}"
bashio::log.info "UDP Port: ${UDP_PORT}"

# Change to app directory
cd /app

# Start web server
exec python3 web_ui.py --gateway "${GATEWAY_IP}" --port "${UDP_PORT}"
