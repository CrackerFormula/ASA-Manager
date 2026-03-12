#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# ARK: Survival Ascended Server Launch Script
# =============================================================================

# Server configuration with defaults
MAP_NAME="${MAP_NAME:-TheIsland_WP}"
SESSION_NAME="${SESSION_NAME:-ARK Server}"
SESSION_NAME="${SESSION_NAME// /%20}"
SERVER_ADMIN_PASSWORD="${SERVER_ADMIN_PASSWORD:-}"
SERVER_PASSWORD="${SERVER_PASSWORD:-}"
MAX_PLAYERS="${MAX_PLAYERS:-70}"
ASA_PORT="${ASA_PORT:-7777}"
QUERY_PORT="${QUERY_PORT:-27015}"
RCON_PORT="${RCON_PORT:-27020}"
RCON_ENABLED="${RCON_ENABLED:-True}"
BATTLEYE="${BATTLEYE:-false}"
MOD_IDS="${MOD_IDS:-}"
CUSTOM_SERVER_ARGS="${CUSTOM_SERVER_ARGS:-}"

# Override settings from web-managed config file if it exists
SERVER_CONFIG="/serverdata/config/server.conf"
if [[ -f "${SERVER_CONFIG}" ]]; then
    # shellcheck disable=SC1090
    source "${SERVER_CONFIG}"
    # Re-encode SESSION_NAME spaces after sourcing
    SESSION_NAME="${SESSION_NAME// /%20}"
fi

# Override MOD_IDS from web-managed config file if it exists
MODS_CONFIG="/serverdata/config/mods.txt"
if [[ -f "${MODS_CONFIG}" ]]; then
    FILE_MODS=$(grep -v '^\s*$' "${MODS_CONFIG}" | tr '\n' ',' | sed 's/,$//')
    if [[ -n "${FILE_MODS}" ]]; then
        MOD_IDS="${FILE_MODS}"
    fi
fi

# Validate required passwords
if [[ -z "${SERVER_ADMIN_PASSWORD}" ]]; then
    echo "ERROR: SERVER_ADMIN_PASSWORD is not set. Refusing to start." >&2
    exit 1
fi

PROTON_VERSION="${PROTON_VERSION:-GE-Proton9-27}"
PROTON="/opt/proton-ge/${PROTON_VERSION}/proton"
ARK_BINARY="/serverdata/ark-server/ShooterGame/Binaries/Win64/ArkAscendedServer.exe"

# Verify required files exist
if [[ ! -f "${PROTON}" ]]; then
    echo "ERROR: Proton-GE not found at ${PROTON}" >&2
    exit 1
fi

if [[ ! -f "${ARK_BINARY}" ]]; then
    echo "ERROR: ArkAscendedServer.exe not found at ${ARK_BINARY}" >&2
    echo "Please install the server via SteamCMD first." >&2
    exit 1
fi

# Build the map/session argument string
SERVER_ARGS="${MAP_NAME}?listen?SessionName=${SESSION_NAME}?RCONEnabled=${RCON_ENABLED}?RCONPort=${RCON_PORT}?ServerAdminPassword=${SERVER_ADMIN_PASSWORD}"

# Append server password if set
if [[ -n "${SERVER_PASSWORD}" ]]; then
    SERVER_ARGS="${SERVER_ARGS}?ServerPassword=${SERVER_PASSWORD}"
fi

# Build launch flags
LAUNCH_FLAGS=(
    "-Port=${ASA_PORT}"
    "-QueryPort=${QUERY_PORT}"
    "-WinLiveMaxPlayers=${MAX_PLAYERS}"
)

# BattlEye toggle
if [[ "${BATTLEYE,,}" == "false" || "${BATTLEYE,,}" == "0" ]]; then
    LAUNCH_FLAGS+=("-NoBattlEye")
fi

# Append mods if specified
if [[ -n "${MOD_IDS}" ]]; then
    LAUNCH_FLAGS+=("-mods=${MOD_IDS}")
fi

# Append any custom args
if [[ -n "${CUSTOM_SERVER_ARGS}" ]]; then
    # shellcheck disable=SC2206
    LAUNCH_FLAGS+=(${CUSTOM_SERVER_ARGS})
fi

echo "Starting ARK: Survival Ascended Server..."
echo "  Map:          ${MAP_NAME}"
echo "  Session:      ${SESSION_NAME}"
echo "  Port:         ${ASA_PORT}"
echo "  Query Port:   ${QUERY_PORT}"
echo "  RCON Port:    ${RCON_PORT}"
echo "  Max Players:  ${MAX_PLAYERS}"
echo "  BattlEye:     ${BATTLEYE}"
[[ -n "${MOD_IDS}" ]] && echo "  Mods:         ${MOD_IDS}"

exec "${PROTON}" run "${ARK_BINARY}" "${SERVER_ARGS}" "${LAUNCH_FLAGS[@]}"
