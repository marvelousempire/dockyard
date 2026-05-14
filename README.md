# Dockyard

> **Docker Desktop minus the bloat.** A lightweight, local-first UI for
> managing containers, images, volumes, and networks — built to work with
> any Docker socket (Colima, OrbStack, Docker Desktop, remote daemons).

## Status

**V0.3 (v0.3.0) — feature-complete for V0.** Every gap closed, every
elevation shipped (Plan 0013). Web terminal exec deferred to v0.4.0.
See **[PRD.md](./PRD.md)** for the design and **[CHANGELOG.md](./CHANGELOG.md)**
for what's in.

```bash
# THE one command (heals Docker Desktop hangs, installs Colima if
# missing, starts the engine, boots Dockyard, opens browser, exposes
# on Wi-Fi LAN). Idempotent — safe to re-run.
make -C dockyard ui
#   ⮕ http://127.0.0.1:4321        (localhost)
#   ⮕ http://192.168.x.y:4321      (your Wi-Fi LAN)

# Localhost only (no Wi-Fi exposure)
make -C dockyard ui-local

# Bare server, no heal / install / browser (for CI / scripts)
make -C dockyard run

# Just diagnose
make -C dockyard doctor

# Or as a Compose service
docker compose up -d dockyard
open https://localhost:4322   # Caddy HTTPS front-door

# Or from any AI agent (MCP)
pnpm dockyard:mcp <<<'{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

### What `make ui` does (Plan 0014)

It's the heal-then-boot path: one command, zero manual steps.

1. **Triage** the Docker engine state (Colima / OrbStack / Docker
   Desktop / native / nothing)
2. **Heal** if Docker Desktop is hung — quit it, sweep stale vsock
   files
3. **Install** Colima via Homebrew if missing (with consent prompt)
4. **Start** Colima with sensible defaults (4 CPU / 6 GB / 60 GB)
5. **Probe** the socket reachability
6. **Boot** Dockyard on `0.0.0.0:4321` (Wi-Fi visible)
7. **Open** the browser at localhost
8. **Print** both URLs so you can hand the Wi-Fi one to another device

Knobs:
- `DOCKYARD_HOST=127.0.0.1` — localhost only
- `DOCKYARD_PORT=4500` — override port
- `DOCKYARD_NO_BROWSER=1` — skip browser
- `DOCKYARD_FORCE_SWEEP=1` — sweep DD even when it looks healthy

### What ships in v0.3.0

- Container / image / volume / network management with status pills
- **Compose-project view** as the default landing screen
- **Live CPU + memory sparklines** per running container
- Streaming logs (chunked HTTP) + image-pull progress (NDJSON)
- **Drag-to-prune** on the Disk view (images, volumes, containers)
- **Engine swapper** — switch Colima ↔ OrbStack ↔ Docker Desktop
  without restart
- **"Ask Claude why"** banner on exited containers — deep-links to
  the main app's `/ask` with logs prefilled
- **MCP server** with 12 tools for AI agents
- `make doctor` with auto-install offer for missing engines
- Caddy HTTPS front-door (`https://localhost:4322`)
- Auto/Light/Dark theme + accent driven by `dockyard.config.json`

## The five-second pitch

Docker Desktop is ~1.5 GB, runs an Electron UI on top of a VM, prompts for
sign-in, and on macOS Tahoe + Apple Silicon it has been crashing on every
restart. We moved the runtime to **[Colima](https://github.com/abiosoft/colima)**
(native Apple Silicon, free, no GUI, exact same `docker` socket).

But Colima has no UI. Dockyard is the UI — a single-page web app served
by a Python 3 standard-library HTTP server that talks to the Docker
Engine API over the local Unix socket. **Zero pip install. Zero npm
install.** < 50 MB on disk.

## What you'll get (P0)

- Container list with status, ports, image, started date
- Start / stop / restart / remove containers
- Streaming logs in the browser
- `docker exec` shell over a web terminal
- Image list, pull, remove
- Volume + network list and inspect
- Live CPU / memory / network stats per container
- Compose project view (containers grouped by project)

See [PRD.md § 11](./PRD.md) for the complete scope.

## Folder roadmap

```
dockyard/
├── README.md            # ← you are here
├── PRD.md               # the design document (read this first)
├── CHANGELOG.md         # version history
├── LICENSE              # MIT
│
├── server.py            # [v0.2.0] Python 3 stdlib HTTP server
├── web/index.html       # [v0.2.0] pre-built single-page UI (Tailwind CDN)
├── dockyard.config.json # [v0.2.0] port, socket, branding, auth
├── Makefile             # [v0.2.0] make run / make doctor / make ui
└── docs/                # [v0.3.0] user guide
```

Same shape as `clinic/`. Eventually extracted to its own GitHub repo
(`marvelousempire/dockyard`) — same path the Clinic is on.

## Provenance

Dockyard was incubated inside
[marvelousempire/claude-chat-reader](https://github.com/marvelousempire/claude-chat-reader)
(plans 0011 → 0014) and graduated to this standalone repo at
**v0.3.1**. The parent repo now references this one as a git
submodule. Same shape as the
[Clinic](https://github.com/marvelousempire/clinic).

## Read next

1. **[PRD.md](./PRD.md)** — the design and decision record
2. [../clinic/README.md](../clinic/README.md) — the pattern Dockyard
   follows
3. [../BLUEPRINT.md](../BLUEPRINT.md) — the stack template Dockyard
   plugs into

## License

MIT — see [LICENSE](./LICENSE).
