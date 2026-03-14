#!/usr/bin/env bash
set -euo pipefail

# Clean stale X11 lock files from previous runs
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1 2>/dev/null || true

# Create required server data directories
mkdir -p \
    /serverdata/logs \
    /serverdata/proton-compat \
    /serverdata/ark-server \
    /serverdata/config

# Set ownership of serverdata to ark user
# Only chown directories that need it (skip the huge ark-server install if already correct)
for dir in /serverdata/logs /serverdata/proton-compat /serverdata/config /serverdata/backups; do
    chown -R ark:ark "$dir" 2>/dev/null || true
done
# Fix top-level ownership without recursing into ark-server
chown ark:ark /serverdata
# Only recurse into ark-server if it exists and has wrong ownership
if [ -d /serverdata/ark-server ]; then
    if [ "$(stat -c '%u' /serverdata/ark-server 2>/dev/null)" != "7777" ]; then
        chown -R ark:ark /serverdata/ark-server
    fi
fi

# SteamCMD needs write access for updates
chown -R ark:ark /opt/steamcmd /root/Steam /root/.steam 2>/dev/null || true

# Ensure machine-id exists (required by Wine/Proton)
[ -f /etc/machine-id ] || python -c "import uuid; print(uuid.uuid4().hex)" > /etc/machine-id

# Ensure protonfixes config dir exists
mkdir -p /home/ark/.config/protonfixes
chown -R ark:ark /home/ark/.config

# Steam SDK paths — required for Steam Game Server API registration
mkdir -p /home/ark/.steam/sdk64 /home/ark/.steam/sdk32
if [ -f /opt/steamcmd/linux64/steamclient.so ]; then
    ln -sf /opt/steamcmd/linux64/steamclient.so /home/ark/.steam/sdk64/steamclient.so
fi
if [ -f /opt/steamcmd/linux32/steamclient.so ]; then
    ln -sf /opt/steamcmd/linux32/steamclient.so /home/ark/.steam/sdk32/steamclient.so
fi
chown -R ark:ark /home/ark/.steam

# Symlink GameUserSettings.ini so the web UI can find it at the config path
# ARK writes the real file under its own Saved/Config directory
INI_REAL="/serverdata/ark-server/ShooterGame/Saved/Config/WindowsServer/GameUserSettings.ini"
INI_LINK="/serverdata/config/GameUserSettings.ini"
if [ -f "${INI_REAL}" ] && [ ! -e "${INI_LINK}" ]; then
    ln -sf "${INI_REAL}" "${INI_LINK}"
fi

# Seed default multiplier settings into [ServerSettings] if missing
if [ -f "${INI_REAL}" ]; then
    DEFAULTS=(
        "TamingSpeedMultiplier=1.000000"
        "GenericXPMultiplier=1.000000"
        "HarvestAmountMultiplier=1.000000"
        "PlayerCharacterWaterDrainMultiplier=1.000000"
        "PlayerCharacterFoodDrainMultiplier=1.000000"
        "PlayerCharacterStaminaDrainMultiplier=1.000000"
        "PlayerCharacterHealthRecoveryMultiplier=1.000000"
        "DinoCharacterFoodDrainMultiplier=1.000000"
        "DinoCharacterStaminaDrainMultiplier=1.000000"
        "DinoCharacterHealthRecoveryMultiplier=1.000000"
        "DamageTakenMultiplier=1.000000"
        "DamageMultiplier=1.000000"
        "StructureResistanceMultiplier=1.000000"
        "XPMultiplier=1.000000"
        "DinoCountMultiplier=1.000000"
        "HarvestHealthMultiplier=1.000000"
        "ResourcesRespawnPeriodMultiplier=1.000000"
        "PlayerResistanceMultiplier=1.000000"
        "DinoResistanceMultiplier=1.000000"
        "DinoDamageMultiplier=1.000000"
        "NightTimeSpeedScale=1.000000"
        "DayTimeSpeedScale=1.000000"
        "MatingIntervalMultiplier=1.000000"
        "EggHatchSpeedMultiplier=1.000000"
        "BabyMatureSpeedMultiplier=1.000000"
        "PassiveTameIntervalMultiplier=1.000000"
    )
    for entry in "${DEFAULTS[@]}"; do
        key="${entry%%=*}"
        if ! grep -qi "^${key}=" "${INI_REAL}"; then
            # Append under [ServerSettings] section
            if grep -qi '^\[ServerSettings\]' "${INI_REAL}"; then
                sed -i "/^\[ServerSettings\]/a ${entry}" "${INI_REAL}"
            else
                printf '\n[ServerSettings]\n%s\n' "${entry}" >> "${INI_REAL}"
            fi
        fi
    done
fi

# Export environment variables for child processes
export DISPLAY="${DISPLAY:-:1}"
export STEAM_COMPAT_DATA_PATH="${STEAM_COMPAT_DATA_PATH:-/serverdata/proton-compat}"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="${STEAM_COMPAT_CLIENT_INSTALL_PATH:-/opt/steamcmd}"
export HOME="${HOME:-/home/ark}"
export LANG="${LANG:-en_US.UTF-8}"
export LC_ALL="${LC_ALL:-en_US.UTF-8}"

# Execute supervisord as PID 1
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
