<div align="center">

# Dockyard

**Local-first UI for the Docker Engine API — without Docker Desktop’s weight.**

*Containers, images, volumes, networks, and Compose grouping over any Unix socket (Colima, OrbStack, Docker Desktop, Linux). Python stdlib server + single-page UI — zero pip, zero npm for Dockyard itself.*

[Quick start](#quick-start) · [What ships](#what-ships-today) · [Environment](#environment-knobs) · [Stack placement](#relationship-to-the-marvelousempire-stack) · [Read order](#read-order) · [Docs](#documents) · [License](#license)

</div>

---

## Status

| | |
|--|--|
| **Release line** | **v0.3.x** — feature-complete for V0 ([CHANGELOG](./CHANGELOG.md)). Web-terminal exec deferred to v0.4. |
| **Design authority** | [PRD.md](./PRD.md) |
| **Born from** | Incubated in [claude-chat-reader](https://github.com/marvelousempire/claude-chat-reader) (plans 0011 → 0014); graduated to **`marvelousempire/dockyard`** at **v0.3.1**. |

---

## What Dockyard does

> **Docker Desktop minus the bloat:** one browser UI talks to whichever engine exposes `docker.sock` — Colima on Apple Silicon, OrbStack, Docker Desktop when it behaves, or `/var/run/docker.sock` on Linux. Same API the CLI uses; different chrome.

Nephew-scale stacks ([Nephew](https://github.com/marvelousempire/nephew), [Automata](https://github.com/marvelousempire/automata), [Claude Archive](https://github.com/marvelousempire/claude-chat-reader)) assume machines can run Compose-backed services without babysitting a hung Electron runtime. Dockyard is the **operator surface** for that socket — not a replacement for the engine, not part of the production request path.

---

## Quick start

### One command (recommended on macOS)

Heals common Docker Desktop hangs, offers Colima install/start, boots Dockyard, opens the browser, optionally binds on LAN.

```bash
git clone https://github.com/marvelousempire/dockyard.git && cd dockyard
make ui
# → http://127.0.0.1:4321           (localhost)
# → http://192.168.x.y:4321         (Wi-Fi — when bound to 0.0.0.0)
```

Localhost-only (no LAN exposure):

```bash
make ui-local
```

### Bare server (CI, scripts, no heal/install/browser)

```bash
make run            # port from dockyard.config.json (default 4321)
make open           # open existing server in browser (does not start)
make doctor         # diagnose host + engine + socket
```

### MCP (AI agents)

From **this repo’s root**:

```bash
make mcp
```

When Dockyard lives **inside** [Claude Archive](https://github.com/marvelousempire/claude-chat-reader) as `dockyard/`:

```bash
pnpm dockyard:mcp <<<'{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

### Compose + HTTPS front-door

In stacks that ship Dockyard beside Caddy (e.g. Claude Archive `docker-compose.yml`):

```bash
docker compose up -d dockyard
open https://localhost:4322    # typical Caddy route — see host project’s Caddyfile
```

---

### What `make ui` does

Plan **0014** — heal-then-boot, idempotent:

1. **Triage** engine state (Colima / OrbStack / Docker Desktop / native / absent).
2. **Heal** hung Docker Desktop — quit, sweep stale socket artefacts where applicable.
3. **Install** Colima via Homebrew if missing (consent prompt).
4. **Start** Colima with conservative defaults (CPU / RAM / disk disk image).
5. **Probe** socket reachability.
6. **Listen** Dockyard on `0.0.0.0:<port>` (LAN-visible unless `DOCKYARD_HOST=127.0.0.1`).
7. **Open** browser at localhost and print URLs.

---

## What ships today

- Containers / images / volumes / networks with status pills  
- **Compose-project view** (default landing)  
- Live **CPU + memory sparklines** per running container  
- Streaming logs + image-pull progress (NDJSON)  
- **Disk** view with drag-to-prune  
- **Engine swapper** — Colima ↔ OrbStack ↔ Docker Desktop without restarting Dockyard  
- **“Ask Claude why”** on exited containers — deep-links to Claude Archive `/ask` when that integration is configured  
- **MCP** tool surface for agents (`make mcp`)  
- **`make doctor`** with actionable fixes  
- Theme + accent from **`dockyard.config.json`**  

Full enumeration: [PRD.md](./PRD.md) (complete scope section).

---

## Environment knobs

| Variable | Effect |
|----------|--------|
| `DOCKYARD_HOST` | Bind address (`127.0.0.1` = localhost only; default wider LAN bind flows via `bin/go`). |
| `DOCKYARD_PORT` | Override listening port (default from config file). |
| `DOCKYARD_NO_BROWSER=1` | Skip opening a browser after boot. |
| `DOCKYARD_FORCE_SWEEP=1` | Aggressive Docker Desktop sweep even when status looks healthy. |

Persistent defaults live in **`dockyard.config.json`** (port, socket probe order, branding, UI cadence).

---

## Relationship to the marvelousempire stack

| Repo | Role |
|------|------|
| [nephew](https://github.com/marvelousempire/nephew) | CLOAK orchestrator — orientation-first agent stack; **does not** ship Dockyard source here. |
| [automata](https://github.com/marvelousempire/automata) | Layer-0 Pad / product truth; Compose templates reference sibling repos. |
| [claude-chat-reader](https://github.com/marvelousempire/claude-chat-reader) | Claude Archive — **git submodule → this repo**; dashboard `/dockyard` embed + `/health` probe (`DOCKYARD_INTERNAL_URL` / `DOCKYARD_PUBLIC_URL`). |
| [clinic](https://github.com/marvelousempire/clinic) | Separate sibling pattern (standalone repo + submodule); same “thin shell + JSON config” ergonomics as Dockyard. |

**GitHub is source of truth** — ship fixes here first; bump the submodule SHA in consuming repos.

---

## Read order

| # | Path | Why |
|---|------|-----|
| 1 | [PRD.md](./PRD.md) | Design + decisions |
| 2 | This README | Operator entrypoints |
| 3 | [CHANGELOG.md](./CHANGELOG.md) | Version facts |
| 4 | [docs/case-study.md](./docs/case-study.md) | Narrative walk-through |
| 5 | [docs/dispatcher.md](./docs/dispatcher.md) | MCP / dispatcher wiring |

---

## Documents

| Doc | Contents |
|-----|----------|
| [PRD.md](./PRD.md) | Scope, architecture, API sketch |
| [CHANGELOG.md](./CHANGELOG.md) | Release history |
| [dockyard.config.json](./dockyard.config.json) | Runtime schema (comments inline) |
| [plans/README.md](./plans/README.md) | Historical plans index |

---

## Repository layout

```
dockyard/
├── README.md              ← you are here
├── PRD.md
├── CHANGELOG.md
├── LICENSE
├── server.py              # stdlib HTTP + Docker API proxy
├── mcp.py                 # stdio MCP for agents
├── web/index.html         # SPA (Tailwind CDN)
├── web/static/
├── dockyard.config.json
├── lib/socket.py          # socket detection
├── bin/go                 # one-keystroke boot (Plan 0014)
├── Makefile
├── Dockerfile
├── scripts/doctor.sh
├── tests/
└── docs/
```

---

## License

MIT — see [LICENSE](./LICENSE).
