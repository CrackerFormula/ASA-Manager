import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_FILE = Path("/serverdata/config/server.conf")

# Keys allowed in server.conf (whitelist to prevent injection)
ALLOWED_KEYS = {
    "MAP_NAME",
    "SESSION_NAME",
    "MAX_PLAYERS",
    "SERVER_PASSWORD",
    "SERVER_ADMIN_PASSWORD",
    "ASA_PORT",
    "QUERY_PORT",
    "RCON_PORT",
    "RCON_ENABLED",
    "BATTLEYE",
    "MOD_IDS",
    "CUSTOM_SERVER_ARGS",
    "STEAM_SERVER_TOKEN",
}


class ServerConfig:
    def __init__(self, path: Path = CONFIG_FILE):
        self._path = path

    def _ensure_dir(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def get_config(self) -> dict[str, str]:
        """Read server.conf and return as dict. Missing file returns empty dict."""
        if not self._path.exists():
            return {}
        result: dict[str, str] = {}
        for line in self._path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key in ALLOWED_KEYS:
                    result[key] = value
        return result

    def set_config(self, data: dict[str, str]) -> dict[str, str]:
        """Merge config values into existing config. Only ALLOWED_KEYS are persisted."""
        self._ensure_dir()
        # Merge with existing config so callers don't need to send all keys
        existing = self.get_config()
        existing.update(data)
        lines = ["# ASA-Manager server configuration", "# Managed by web UI — changes take effect on next server start", ""]
        for key, value in existing.items():
            key = key.strip()
            if key not in ALLOWED_KEYS:
                logger.warning("Ignoring unknown config key: %s", key)
                continue
            value = self._sanitize_value(key, str(value))
            # Quote values that contain spaces
            if " " in value:
                lines.append(f'{key}="{value}"')
            else:
                lines.append(f"{key}={value}")
        lines.append("")
        self._path.write_text("\n".join(lines))
        # Redact passwords in log output
        safe_log = {
            k: "***" if "PASSWORD" in k else v
            for k, v in existing.items() if k in ALLOWED_KEYS
        }
        logger.info("Server config saved: %s", safe_log)
        return self.get_config()

    @staticmethod
    def _sanitize_value(key: str, value: str) -> str:
        """Remove shell-dangerous characters from config values."""
        # Strip characters that could cause shell injection when sourced
        dangerous = set('`$;|&\n\r\\')
        if key == "CUSTOM_SERVER_ARGS":
            # Allow hyphens, equals, dots, slashes but still strip injection chars
            return "".join(c for c in value if c not in dangerous)
        # For all other keys, also strip double quotes (they're added by the writer)
        dangerous.add('"')
        return "".join(c for c in value if c not in dangerous)


server_config = ServerConfig()
