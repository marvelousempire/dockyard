# Changelog — Dockyard

All notable changes to Dockyard are recorded here.
Versioning follows [SemVer](https://semver.org/).

---

## [0.1.0] — 2026-05-14

### Born

- Folder seeded inside `claude-chat-reader/dockyard/` following the
  Clinic pattern.
- **PRD.md** written — two-part document:
  - Part 1: **Why Colima instead of Docker Desktop** — the decision
    record (specific incident on macOS Tahoe 26.3.1 + Apple Silicon,
    technical breakdown, trade-offs vs. Docker Desktop / OrbStack /
    Podman, migration playbook).
  - Part 2: **Dockyard PRD** — lightweight Docker Desktop replacement
    UI. Python 3 stdlib server + single-file HTML web UI. P0 scope:
    containers, images, volumes, networks, logs, exec, stats, Compose
    project view. < 50 MB total install.
- **README.md** written — 5-second pitch + status + folder roadmap.
- **LICENSE** added (MIT, mirrored from `clinic/LICENSE`).
- Decision logged in `plans/0011-colima-decision-and-dockyard-app.md`.

### Pre-build

No code yet. The PRD is the deliverable for this version. Implementation
starts at v0.2.0.

---

## [0.2.0] — 2026-05-14

### Added (Plan 0012)

- **`server.py`** — Python 3 stdlib HTTP server (~530 lines). Talks
  Docker Engine API over Unix socket (`http.client.HTTPConnection`
  subclass with `socket.AF_UNIX`). Streams logs and stats via chunked
  transfer. Routes: `/api/containers`, `/api/images`, `/api/volumes`,
  `/api/networks`, `/api/system`, `/api/system/df`, `/api/health`,
  start/stop/restart/remove/pause/unpause, image pull, prune.
- **`web/index.html`** — single-page UI (~530 lines). Tailwind CDN +
  vanilla JS. Sidebar nav. **Compose-project view as default landing**.
  Live status pills (running / paused / exited). Logs slide-over with
  streaming tail. Disk-usage tab with breakdown table + one-click
  prune. Auto / Light / Dark theme toggle.
- **`lib/socket.py`** — auto-detect Colima default + named profiles,
  OrbStack, Docker Desktop, native Linux, `DOCKER_HOST` env var. CLI:
  `python -m dockyard.lib.socket detect`.
- **`dockyard.config.json`** — schema for port, socket path,
  branding, UI defaults.
- **`Makefile`** — `make run`, `make ui`, `make ui-local`, `make
  doctor`, `make test`, `make mcp`, `make status`, `make clean`.
- **`scripts/doctor.sh`** — checks Python, engine install, engine
  running, socket reachability, port availability. Color output,
  graceful suggestions.
- **`mcp.py`** — MCP stdio server (JSON-RPC 2.0). 12 tools exposed:
  list/start/stop/restart/remove containers, tail logs, list/pull/
  remove images, list volumes, list networks, system info. Wire into
  Claude Code via `mcpServers` config.
- **`dockyard.caddyfile`** — Caddyfile snippet for `dockyard.localhost`
  with `tls internal`, security headers (HSTS, CSP, etc.), WebSocket
  upgrade for the future exec terminal.
- **`tests/test_socket.py`** — 15 unit tests (socket detect probes,
  config merge, explicit path validation).
- **`tests/test_endpoints.py`** — 7 integration tests against a real
  Docker socket (skip-gracefully when unreachable).
- **`docs/case-study.md`** — "The Clinic pattern, applied a third
  time" — BLUEPRINT reinforcement essay.
- **PRD update** — "Platform support" subsection (macOS / Linux /
  WSL2 / remote-daemon paths).
- **`/health` page integration** (main app) — Dockyard row showing
  engine, version, socket; status pill (green/amber/gray) for
  reachable/unreachable/not-running.

### Deferred

- Web terminal (`docker exec` over WebSocket) — moved to v0.3.0.
  Python stdlib doesn't speak WebSocket natively; needs ~200 lines
  of RFC 6455 framing + Docker hijack handling.
- Webhook outbox for container events — V1.
- Multi-engine switcher UI — V1.

---

## Upcoming

### [0.3.0] — planned

- Web terminal (`docker exec` over WebSocket).
- Engine switcher (Colima ↔ OrbStack ↔ Docker Desktop) UI.
- Image-pull progress in the UI.
- Container env / resource limit edit.

### [1.0.0] — planned

- Extracted to its own GitHub repo (`marvelousempire/dockyard`).
- Public release.
