#!/usr/bin/with-contenv bashio

# Get configuration
GATEWAY_IP=$(bashio::config 'gateway_ip')
UDP_PORT=$(bashio::config 'udp_port')

bashio::log.info "Starting TIS Control Web UI..."
bashio::log.info "Gateway IP: ${GATEWAY_IP}"
bashio::log.info "UDP Port: ${UDP_PORT}"

# Start web server
exec python3 /web_ui.py --gateway "${GATEWAY_IP}" --port "${UDP_PORT}"
