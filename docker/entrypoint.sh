#!/usr/bin/env bash
set -euo pipefail

# Create required server data directories
mkdir -p \
    /serverdata/logs \
    /serverdata/proton-compat \
    /serverdata/ark-server \
    /serverdata/config

# Set ownership of serverdata to ark user
chown -R ark:ark /serverdata

# Export environment variables for child processes
export DISPLAY="${DISPLAY:-:1}"
export STEAM_COMPAT_DATA_PATH="${STEAM_COMPAT_DATA_PATH:-/serverdata/proton-compat}"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="${STEAM_COMPAT_CLIENT_INSTALL_PATH:-/opt/steamcmd}"
export HOME="${HOME:-/home/ark}"
export LANG="${LANG:-en_US.UTF-8}"
export LC_ALL="${LC_ALL:-en_US.UTF-8}"

# Execute supervisord as PID 1
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
