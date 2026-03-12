# ASA Manager

ASA Manager is a Dockerized ARK: Survival Ascended dedicated server with a browser-based management interface. It automates server installation via SteamCMD and provides a web UI for starting and stopping the server, editing `GameUserSettings.ini`, streaming live logs, and sending RCON commands — no command-line interaction required after initial setup. Built on Arch Linux with Proton-GE for Wine-based ARK compatibility on Linux hosts.

---

## Requirements

| Resource | Minimum |
|---|---|
| RAM | 16 GB (ARK: SA is memory-intensive) |
| Disk | 25 GB free for server files + saves |
| OS | Any Linux host with Docker; Unraid 6.10+ |
| Docker | Docker Engine + Compose v2 |

---

## Quick Start

```bash
git clone https://github.com/CrackerFormula/asa-manager.git
cd asa-manager
cp .env.example .env        # optional: edit defaults
docker compose up -d
```

Open **http://localhost:8080** in your browser. On first run, click **Install** to download the ARK server files (~15 GB via SteamCMD). Once complete, click **Start Server**.

---

## Unraid Installation

1. In Unraid, open the **Apps** tab and search for **ASA Manager**.
2. Click **Install** on the template and review the settings.
3. Set a strong **Admin Password** before clicking Apply.
4. After the container starts, open the Web UI link shown in the Docker tab.
5. Click **Install** in the web UI to download server files, then **Start Server**.

To add the template manually: go to **Settings → Community Applications → Extra template repositories** and add:

```
https://raw.githubusercontent.com/CrackerFormula/asa-manager/main/unraid/ark-survival-ascended.xml
```

Server files and saves are stored in `/mnt/user/appdata/asa-manager` on your array.

---

## Environment Variables

Set these in a `.env` file alongside `docker-compose.yml`, or via the Unraid template UI.

| Variable | Default | Description |
|---|---|---|
| `INSTANCE_NAME` | `ASA_Server_1` | Unique name for this server instance |
| `TZ` | `America/New_York` | Container timezone (e.g. `America/Los_Angeles`, `UTC`) |
| `MAP_NAME` | `TheIsland_WP` | Map to load: `TheIsland_WP`, `Aberration_WP`, `ScorchedEarth_WP`, `TheCenter_WP` |
| `SESSION_NAME` | `My ARK Server` | Server name shown in the in-game browser |
| `SERVER_ADMIN_PASSWORD` | `ChangeMe123` | Admin/RCON password — **change this** |
| `SERVER_PASSWORD` | *(empty)* | Join password; leave blank for a public server |
| `MAX_PLAYERS` | `70` | Maximum concurrent players |
| `ASA_PORT` | `7777` | Game port the server binds to |
| `RCON_PORT` | `27020` | RCON port |
| `RCON_ENABLED` | `TRUE` | Enable RCON (`TRUE`/`FALSE`) |
| `BATTLEYE` | `FALSE` | Enable BattlEye anti-cheat (`TRUE`/`FALSE`) |
| `MOD_IDS` | *(empty)* | Comma-separated CurseForge mod IDs (e.g. `927090,880477`) |
| `CUSTOM_SERVER_ARGS` | *(empty)* | Extra arguments appended to the server launch command |
| `INI_PATH` | `/serverdata/config/GameUserSettings.ini` | Path to the settings INI inside the container |
| `ARK_LOG_PATH` | `/serverdata/ark-server/ShooterGame/Saved/Logs/ShooterGame.log` | Path to the ARK log file inside the container |
| `SERVER_DIR` | `/serverdata/ark-server` | Server installation directory inside the container |

Example `.env`:

```env
INSTANCE_NAME=MyServer
TZ=America/Chicago
SESSION_NAME=My Tribe Server
SERVER_ADMIN_PASSWORD=supersecret
MAX_PLAYERS=20
MOD_IDS=927090,880477
```

---

## Accessing the Web UI

| URL | Purpose |
|---|---|
| `http://<host-ip>:8080` | Main management interface |

The web UI provides:
- **Server controls** — Start, Stop, Restart, Install/Update
- **Status badge** — live RUNNING / STOPPED indicator with uptime and player count
- **Settings editor** — edit `GameUserSettings.ini` sections directly in the browser
- **Live log viewer** — real-time server log tail with color-coded error/warning lines
- **RCON** — graceful shutdown uses saveworld + doexit via RCON automatically

---

## Installing the ARK Server Files

**Via the Web UI (recommended):**

1. Open `http://<host-ip>:8080`
2. Click **Install** (or **Update** if previously installed)
3. Watch progress in the log viewer — SteamCMD downloads ~15 GB
4. Once complete, click **Start Server**

**Manual SteamCMD (advanced):**

```bash
docker exec -it asa-manager bash
steamcmd +force_install_dir /serverdata/ark-server \
         +login anonymous \
         +app_update 2430930 validate \
         +quit
```

---

## Updating the Server

Click **Install** in the web UI at any time to run `app_update` via SteamCMD. The server must be stopped first — the UI will warn you if it's running. Saves and config are preserved in `/serverdata` and are not affected by updates.

---

## Port Forwarding

Forward these ports on your router to make the server reachable from the internet:

| Port | Protocol | Required |
|---|---|---|
| `7777` | UDP | Yes — primary game traffic |
| `7777` | TCP | Yes — game traffic (TCP) |
| `7778` | UDP | Yes — raw UDP (GamePort+1) |
| `27020` | TCP | Optional — RCON only (do not expose publicly) |
| `8080` | TCP | Optional — web UI (do not expose publicly) |

Point them at the LAN IP of your Docker or Unraid host.

---

## Known Limitations

- **Proton-GE on Linux:** ARK: Survival Ascended is a Windows-only binary. This image uses Proton-GE (Wine-based) to run it on Linux. Compatibility may vary with ARK updates; if the server fails to start after an update, check for a newer Proton-GE release.
- **BattlEye:** BattlEye anti-cheat (`BATTLEYE=TRUE`) is not reliably supported under Proton/Wine and may prevent the server from starting. Leave it disabled unless you have confirmed it works with your setup.
- **First start time:** The server can take 2–5 minutes to fully initialize and appear in the in-game browser after clicking Start.
- **Memory:** ARK: SA regularly uses 8–12 GB of RAM under load. On hosts with less than 16 GB total, the OS may OOM-kill the process.
- **ARM hosts:** This image targets `linux/amd64` only. Raspberry Pi and other ARM hosts are not supported.

---

## Building from Source

```bash
git clone https://github.com/CrackerFormula/asa-manager.git
cd asa-manager
docker build -t crackerformula/asa-manager:latest .
docker compose up -d
```

Build time is approximately 10–20 minutes depending on your connection speed (downloads Proton-GE and bootstraps SteamCMD).

---

## License

MIT License — see [LICENSE](LICENSE).
