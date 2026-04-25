#!/usr/bin/with-contenv bashio

set -e

LOG_LEVEL="$(bashio::config 'log_level')"
export LOG_LEVEL

bashio::log.info "Starting Mojelektro Mini"

exec python3 /usr/src/mojelektro_mini/main.py
