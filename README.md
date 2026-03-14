# ASA Manager

A Dockerized **ARK: Survival Ascended** dedicated server with a browser-based management UI. Install, configure, and manage your server entirely from a web dashboard — no command line needed after the initial container setup.

Built on Arch Linux with Proton-GE to run the Windows ARK server binary on Linux. Designed for Unraid but works on any Docker host.

---

## Features

- **One-click install & update** — Downloads server files via SteamCMD directly from the web UI
- **Start / Stop / Restart** — Graceful shutdown with world save via RCON before stopping
- **Live server logs** — Real-time log streaming with color-coded output
- **Server configuration** — Change map, server name, max players, passwords, ports, and more from the UI — no container recreation needed
- **INI settings editor** — Edit `GameUserSettings.ini` sections with a tabbed interface
- **Mod management** — Add and remove CurseForge mod IDs
- **Backup & restore** — Compressed snapshots of save data with safe restore (extracts to temp dir, verifies, then swaps)
- **Scheduled restarts** — Set daily restart times with a simple time picker
- **Live player count** — Via RCON
- **Session-based auth** — Password-protected web UI with rate-limited login

---

## Quick Start

### Docker Compose

```yaml
services:
  asa-manager:
    image: crackerformula/asa-manager:latest
    container_name: asa-manager
    restart: unless-stopped
    ports:
      - "7777:7777/udp"    # Game port
      - "7777:7777/tcp"    # Game port (TCP)
      - "7778:7778/udp"    # Raw UDP (Game port + 1)
      - "27015:27015/udp"  # Steam query (server browser)
      - "27020:27020/tcp"  # RCON
      - "8080:8080/tcp"    # Web UI
    volumes:
      - ./serverdata:/serverdata
    environment:
      - WEB_PASSWORD=your-secure-password
      - SERVER_ADMIN_PASSWORD=your-admin-password
      - TZ=America/New_York
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

```bash
docker compose up -d
```

### Unraid

1. Copy `unraid/asa-manager.xml` to `/boot/config/plugins/dockerMan/templates-user/` on your Unraid flash drive
2. Go to **Docker** → **Add Container** → select **ASA-Manager** from the template dropdown
3. Set **WEB_PASSWORD** and **Admin Password**
4. Click **Apply**

Server files and saves persist at `/mnt/user/appdata/asa-manager` on your array.

### First Run

1. Open `http://<your-ip>:8080` in a browser
2. Log in with your `WEB_PASSWORD`
3. Click **Install/Update** — downloads ~15 GB of server files via SteamCMD
4. Once installed, click **Start Server**
5. The server takes 2–5 minutes to fully initialize and appear in the Steam server browser

---

## How It Works

### Architecture

```
┌──────────────────────────────────────────────┐
│  Docker Container                            │
│                                              │
│  supervisord (PID 1)                         │
│  ├── Xvfb            virtual display         │
│  ├── arkserver        Proton → ARK .exe      │
│  └── webui            Uvicorn + FastAPI       │
│                                              │
│  /serverdata/         (persistent volume)     │
│  ├── ark-server/      game files (~15 GB)     │
│  ├── config/          server.conf, INI, mods  │
│  ├── backups/         tar.gz snapshots        │
│  ├── proton-compat/   Wine/DXVK prefix        │
│  └── logs/            supervisord logs        │
└──────────────────────────────────────────────┘
```

**supervisord** manages three processes:

| Process | Purpose | Startup |
|---------|---------|---------|
| **Xvfb** | Virtual X display required by Proton/Wine | Auto |
| **arkserver** | ARK server via `start_ark.sh` → Proton → `ArkAscendedServer.exe` | Manual (click Start in UI) |
| **webui** | FastAPI on port 8080 | Auto |

### Server Lifecycle

**Starting:** Web UI → supervisord → `start_ark.sh` → Proton-GE → `ArkAscendedServer.exe`

**Stopping (graceful):**
1. `saveworld` sent via RCON (waits 30 seconds for the save to complete)
2. `doexit` sent via RCON (waits 10 seconds for clean exit)
3. If still running, supervisord sends SIGTERM, then SIGKILL after 60 seconds

### Configuration Flow

The server reads settings from two sources, with the second overriding the first:

1. **Environment variables** (Docker/Unraid) — used as initial defaults
2. **`/serverdata/config/server.conf`** (managed by web UI) — overrides env vars at launch

This means you set required passwords in your Docker config, then manage everything else from the web UI without recreating the container. Changes in the web UI are saved to `server.conf` immediately and take effect on the next server start.

---

## Web UI Panels

### Control Bar
Start, stop, restart, and install/update the server. Shows live status (running / stopped / stopping), uptime, and player count. Restart requires confirmation since it disconnects active players.

### Server Configuration
Change map (dropdown with all official maps), server name, max players, passwords, ports, BattlEye, RCON, and custom launch arguments. Saved to `server.conf` — changes apply on next server start.

### INI Settings Editor
Edit `GameUserSettings.ini` with a tabbed interface organized by section. Fields auto-detect type (boolean toggles, number inputs, password fields, map dropdowns). Useful for tweaking XP rates, taming speeds, harvest amounts, and other gameplay settings.

### Server Logs
Real-time log viewer with color-coded output — errors in red, warnings in yellow. Auto-scroll toggle and clear button. Streams via Server-Sent Events so the page stays responsive.

### Mod Management
Add CurseForge mod IDs. Stored in `/serverdata/config/mods.txt` and passed to the server as `-mods=id1,id2,...` on launch.

### Scheduled Restarts
Set daily restart times using a time picker (24-hour format, container local time). The scheduler checks every 30 seconds and triggers a full graceful restart (save → stop → start) when the time matches.

### Backups
Create compressed tar.gz snapshots of the `Saved` directory. Restore is safe — extracts to a temp directory first, verifies the expected structure exists, then swaps. A failed extraction won't destroy your existing saves. Auto-prunes to keep the 10 most recent backups.

---

## Data Persistence

Everything lives under `/serverdata/` (your mounted volume):

| Path | Contents |
|------|----------|
| `ark-server/` | Game server files installed by SteamCMD |
| `ark-server/ShooterGame/Saved/` | World saves and player data |
| `config/server.conf` | Web-managed server settings (map, name, players, etc.) |
| `config/GameUserSettings.ini` | ARK gameplay settings (editable via INI panel) |
| `config/mods.txt` | Mod IDs, one per line |
| `config/schedule.json` | Scheduled restart times |
| `backups/` | Compressed backup archives |
| `proton-compat/` | Proton/Wine prefix data |
| `logs/` | supervisord, ARK, and web UI log files |

Updates via SteamCMD only touch `ark-server/` — your config, saves, and backups are not affected.

---

## Environment Variables

### Required (set in Docker / Unraid)

| Variable | Description |
|----------|-------------|
| `WEB_PASSWORD` | Password for the web UI login. Container will not start without this. |
| `SERVER_ADMIN_PASSWORD` | RCON and in-game admin password. Required by the ARK launch script. |

### Optional (Docker-level)

| Variable | Default | Description |
|----------|---------|-------------|
| `TZ` | `America/New_York` | Container timezone — affects scheduled restarts and log timestamps |
| `SECRET_KEY` | *(derived from WEB_PASSWORD)* | Explicit session signing key. Sessions are derived from `WEB_PASSWORD` by default, so changing your password invalidates all sessions. Set this to decouple them. |
| `SESSION_MAX_AGE` | `86400` | Session cookie lifetime in seconds (default: 24 hours) |
| `SECURE_COOKIES` | `false` | Set to `true` if accessing the web UI through an HTTPS reverse proxy |
| `ASA_PORT` | `7777` | Game port — must match your Docker port mapping |
| `QUERY_PORT` | `27015` | Steam server browser query port — must match your Docker port mapping |
| `RCON_PORT` | `27020` | RCON port — must match your Docker port mapping |
| `RCON_ENABLED` | `True` | Enable RCON (required for graceful shutdown and player count) |
| `INSTANCE_NAME` | `ASA_Server_1` | Internal Proton prefix name |

### Managed by Web UI

These settings are managed through the web UI's Server Configuration panel. They can also be passed as env vars for initial defaults, but the web UI is the intended way to change them:

`MAP_NAME` · `SESSION_NAME` · `MAX_PLAYERS` · `SERVER_PASSWORD` · `BATTLEYE` · `MOD_IDS` · `CUSTOM_SERVER_ARGS`

---

## Ports

| Port | Protocol | Purpose | Forward on Router? |
|------|----------|---------|-------------------|
| 7777 | UDP + TCP | ARK game traffic | Yes |
| 7778 | UDP | ARK raw UDP (game port + 1) | Yes |
| 27015 | UDP | Steam server browser query | Yes — required for server list visibility |
| 27020 | TCP | RCON remote console | No — internal only |
| 8080 | TCP | Web management UI | No — LAN access recommended |

---

## Networking Modes

**Bridge (default):** Standard Docker networking with port mappings. Use the docker-compose example above.

**Bridged / macvlan (Unraid br0):** Container gets its own IP on your LAN. No port mapping needed — all ports are directly accessible. In Unraid, set the network to `br0` and assign a static IP.

---

## Updating the Server

Click **Install/Update** in the web UI at any time to run SteamCMD's `app_update`. The server must be stopped first. Saves and config are preserved — only game files in `ark-server/` are updated.

---

## Security

- The web UI should only be exposed on your LAN. For remote access, put it behind a reverse proxy with HTTPS and set `SECURE_COOKIES=true`.
- Login is rate-limited to 5 attempts per minute per IP.
- Session cookies are httponly, samesite=strict.
- `server.conf` values are sanitized — dangerous shell characters are stripped, and only whitelisted keys are accepted.
- Passwords are redacted in log output.
- Backup filenames are validated to prevent path traversal.

---

## Troubleshooting

### Server won't start
- Make sure you've run **Install/Update** first — the ARK binary must exist
- Check the **Server Logs** panel for error messages
- Verify `SERVER_ADMIN_PASSWORD` is set — the launch script refuses to start without it

### Server not visible in Steam browser
- Forward port **27015/udp** on your router
- Verify the `QUERY_PORT` env var matches your port mapping
- It can take several minutes after starting for the server to appear in the list

### "Not authenticated" in the web UI
- Your session may have expired (default: 24 hours)
- If you changed `WEB_PASSWORD`, sessions signed with the old password are invalidated. Set `SECRET_KEY` explicitly to avoid this.

### High memory usage
- ARK: Survival Ascended typically uses 8–12 GB RAM — this is normal
- The Proton/Wine layer adds some overhead
- Lower `MAX_PLAYERS` if memory is tight

---

## System Requirements

| Resource | Minimum |
|----------|---------|
| **CPU** | x86_64 (AMD64) — ARM is not supported |
| **RAM** | 16 GB (ARK uses 8–12 GB under load) |
| **Disk** | ~25 GB for server files + space for saves and backups |
| **OS** | Any Linux with Docker, or Unraid 6.x+ |

---

## Building from Source

```bash
git clone https://github.com/CrackerFormula/asa-manager.git
cd asa-manager
docker build -t crackerformula/asa-manager:latest .
```

The multi-stage Dockerfile handles everything:
1. **arch-base** — Arch Linux with graphics libraries and system dependencies
2. **steamcmd** — Downloads and bootstraps SteamCMD
3. **proton-ge** — Downloads Proton-GE (default: GE-Proton9-27)
4. **python-venv** — Python 3.12 with FastAPI and dependencies
5. **final** — Assembles all stages into the runtime image (~3 GB)

Build time is approximately 10–20 minutes depending on your connection speed.

---

## License

MIT
