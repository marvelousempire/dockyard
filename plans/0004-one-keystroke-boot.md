> **Provenance:** Originally [plans/0014-dockyard-one-keystroke-boot.md](https://github.com/marvelousempire/claude-chat-reader/blob/main/plans/0014-dockyard-one-keystroke-boot.md)
> in marvelousempire/claude-chat-reader. Copied here Plan 0015/0016 so the
> Dockyard's standalone repo carries its full design history.

# Plan 0014 — Dockyard one-keystroke boot (heal Docker Desktop + switch to Colima + open browser on Wi-Fi)

Status: shipping in this delivery

## Context

`make -C dockyard ui` currently assumes the engine is healthy. On this
machine and any other macOS Tahoe + Apple Silicon, Docker Desktop hangs
randomly (the bug behind Plan 0011) and the user has to manually:

1. Quit Docker Desktop
2. `kill -9` `com.docker.backend` stragglers
3. Wipe stale vsock files
4. Install Colima (if not yet)
5. `colima start`
6. THEN run `make -C dockyard ui`

Marvin wants one command that does all of that **plus** opens the
browser **plus** exposes Dockyard on the Wi-Fi LAN. From zero to
running, no manual steps.

## Approach

Add `dockyard/bin/go` — a single bash script that runs the full triage
→ heal → install → start → boot → open flow. Wire `make -C dockyard ui`
to call it. Keep `make run` as the bare server for scripts/CI.

### Boot flow

```
┌─────────────────────────────────────────────────────────────┐
│  Triage current engine state                                │
└────┬────────────────────────────────────────────────────────┘
     │
     ├── Colima running?            → use it (idempotent)
     ├── OrbStack running?          → use it
     ├── Native /var/run reachable? → use it
     ├── Docker Desktop running?    → quit DD, install/start Colima
     ├── Docker Desktop HUNG?       → sweep + install/start Colima
     └── Nothing installed?         → install + start Colima
                                       │
                                       ▼
                              Probe socket reachable
                                       │
                                       ▼
                       Kill prior Dockyard, start on 0.0.0.0:4321
                                       │
                                       ▼
                              Print banner (localhost + Wi-Fi)
                                       │
                                       ▼
                                  Open browser
```

### Sweep steps (when DD is hung)

1. `osascript -e 'quit app "Docker"'` (gentle)
2. `pkill -9 -f "Docker Desktop"`, `com.docker.backend`,
   `com.docker.virtualization`, `com.docker.helper`,
   `com.docker.dev-envs`
3. Remove stale vsock files:
   - `~/Library/Containers/com.docker.docker/Data/vms/0/00000002.shutdown`
   - `~/Library/Containers/com.docker.docker/Data/vms/0/00000002.sock`
4. Remove the dangling raw socket:
   - `~/Library/Containers/com.docker.docker/Data/docker.raw.sock`

This wipe is **only** triggered when `/_ping` times out on the DD
socket — proof of hang. Otherwise DD is left alone.

### Install steps (when no engine present)

1. Check for Homebrew. If missing, print the official install one-liner
   and stop.
2. Prompt the user (TTY only): "Install Colima now? [Y/n]"
3. `brew install colima docker docker-compose`
4. `colima start --cpu 4 --memory 6 --disk 60` (sensible defaults)

### LAN exposure

Server bound to `0.0.0.0:4321` by default (was `127.0.0.1`). Banner
prints both:

```
URL        http://127.0.0.1:4321
Network    http://192.168.x.y:4321
```

LAN IP detected via `ipconfig getifaddr en0` (macOS) or
`socket.connect(8.8.8.8:80)` trick (cross-platform).

For users who don't want LAN exposure: `DOCKYARD_HOST=127.0.0.1
make -C dockyard ui` or `make -C dockyard ui-local`.

## Critical files

### New
- `dockyard/bin/go` — the heal-then-boot script (~200 lines)

### Modified
- `dockyard/Makefile` — `ui` target now calls `bin/go`; add `boot`
  alias; keep `run` as the bare server
- `dockyard/server.py` — banner shows Network URL when bound to 0.0.0.0
- `package.json` — `pnpm dockyard:ui` calls the script too
- `dockyard/CHANGELOG.md` — v0.3.1 entry
- `dockyard/README.md` — updated entry-point block
- `plans/README.md` — index row for 0014

## Verification

```bash
# 1. From a clean state (DD hung): one command brings everything up
make -C dockyard ui
# expect:
#   - DD quit + swept (if it was hung)
#   - Colima installed (if absent + brew available + user consented)
#   - Colima started (if not running)
#   - Dockyard up on 0.0.0.0:4321
#   - Browser opens
#   - Banner shows both http://127.0.0.1:4321 and http://<lan-ip>:4321

# 2. Idempotent — running again does nothing destructive
make -C dockyard ui
# expect: "Colima already running" + "Dockyard already up" + browser

# 3. Local-only escape hatch
DOCKYARD_HOST=127.0.0.1 make -C dockyard ui
# expect: Network URL omitted from banner

# 4. From another device on the same Wi-Fi
curl http://<your-lan-ip>:4321/api/config
# expect: JSON config response
```

## Out of scope

- Auto-uninstall Docker Desktop (we quit it, we don't remove it —
  users may want it for other purposes)
- Auto-update Colima (`brew upgrade colima` left to user)
- Cloud / tunnel exposure (no ngrok / cloudflared) — local LAN only

## Why this isn't `./go` at the repo root

The main repo already has a `./go` for the dashboard + db + caddy
stack. This script is Dockyard-specific. Keeping it under
`dockyard/bin/` keeps the sub-app self-contained and ready for the
eventual extraction to its own GitHub repo.
