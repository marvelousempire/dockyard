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

- Web terminal (`docker exec` over WebSocket) — moved to v0.4.0.
  Python stdlib doesn't speak WebSocket natively; needs ~200 lines
  of RFC 6455 framing + Docker hijack handling.
- Webhook outbox for container events — V1.

---

## [0.3.0] — 2026-05-14

The gap+elevation pass. All 8 gaps closed and all 8 elevations
shipped (Plan 0013) in one delivery.

### Added — gaps closed

- **G1** — Branding accent now read from `dockyard.config.json` and
  injected as CSS variable. Change `accent` in config → reload UI
  → every accent shifts.
- **G2** — `ui.default_theme` honored when no `localStorage` choice
  exists. `ui.sparkline_seconds` and `ui.show_ai_assist` added.
- **G3** — Header shows an "engine colima · v0.x.x" pill (full
  version surfaced, not just the sidebar engine name).
- **G4** — "+ Pull image" button on the Images view → modal with
  streaming progress (NDJSON from `/api/images/pull`).
- **G5** — `web/static/favicon.svg` + `web/static/dockyard.svg`
  (wordmark). Server's static handler serves them at `/static/…`.
- **G6** — Makefile clarified. New target `make open` opens the
  browser at a running server's URL (separate from `make ui` which
  also starts it). `make docker-build` + `make docker-run` added.
- **G7** — `make doctor` now prints the one-liner to install Colima,
  OrbStack, Docker Desktop, or Linux docker.io when no engine
  exists. Interactive Homebrew install offer when on a TTY.
- **G8** — Cursor rule (`.mdc`) smoke-test procedure documented in
  the plan-first manual smoke section of plan 0013.

### Added — elevations shipped

- **E-A** — Live CPU + memory sparklines per container row (SVG,
  trailing 30 s window, polled via `/api/containers/{id}/stats?stream=0`).
- **E-B** — "Restart all" button on each Compose project group →
  `POST /api/projects/{name}/restart` iterates every container in
  the project.
- **E-C** — "🤖 Ask Claude why (exit N)" banner on exited
  containers with non-zero exit codes. Deep-links into the main
  app's `/ask?q=<prefilled>&autosubmit=1`. Main app's `AskBox`
  now reads `?q=` and `?autosubmit=1` params.
- **E-D** — `dockyard/Dockerfile` (slim, ~50 MB). Added as a
  service in the root `docker-compose.yml`. `caddy/Caddyfile`
  routes `localhost:4322` → `dockyard:4321` with `tls internal`
  and standard security headers. `docker compose up dockyard`
  works.
- **E-E** — `pnpm dockyard:mcp` script (+ `dockyard`, `dockyard:ui`,
  `dockyard:doctor`, `dockyard:test`). `docs/dispatcher.md`
  documents Claude Code / Cursor / generic MCP wiring.
- **E-F** — Drag-to-prune on the Disk view. Images, volumes, and
  containers are draggable; a trash zone confirms + deletes.
- **E-G** — Engine swapper dropdown in the sidebar. Lists every
  detected engine + active marker; selecting one calls
  `POST /api/socket/swap` and live-switches the runtime socket
  without restart.
- **E-H** — Plan-first rule smoke test procedure documented in
  plan 0013 + this changelog. Manual verification: open new
  Claude Code chat, ask for a substantive change, expect plan
  mode auto-entry.

### Added — server endpoints

- `GET /api/config` — runtime config + `_runtime: {engine, socket}`.
- `GET /api/sockets` — every detected engine with `active` /
  `reachable` flags.
- `POST /api/socket/swap` — swap active socket at runtime (probes
  /_ping before committing).
- `POST /api/projects/{name}/restart` — restart every container in
  a Compose project.

### Internal

- Server's startup probe moved AFTER port bind so banner + first
  HTTP response land in <1 s even when the engine is hung.
- Test suite split into `TestServerOnly` (no docker needed) and
  `TestEndpoints` (skips when docker is unreachable). 20 tests pass
  on any machine, 7 more pass when docker is up.

### Verification

```
make -C dockyard test            # 20 ok, 7 skipped (no docker)
make -C dockyard doctor           # diagnoses + offers fixes
python3 -u dockyard/server.py     # banner < 1s, port bound
pnpm exec tsc --noEmit            # clean
```

---

## Upcoming

### [0.4.0] — planned

- Web terminal (`docker exec` over WebSocket).
- Container env / resource-limit editor.
- Image-pull progress with cancel.

### [1.0.0] — planned

- Extracted to its own GitHub repo (`marvelousempire/dockyard`).
- Public release.
