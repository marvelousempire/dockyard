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

## Upcoming

### [0.2.0] — planned

- `server.py` — Python 3 stdlib HTTP server, talks to Docker Engine API
  over Unix socket (`~/.colima/default/docker.sock` by default).
- `web/index.html` — single-page UI (Tailwind CDN, vanilla JS).
- `dockyard.config.json` — port, socket path, branding, auth mode.
- `Makefile` — `make run` / `make doctor` / `make ui`.
- P0 features: container list, start/stop/restart/remove, logs stream,
  image list/pull/remove, volume + network list, live stats.

### [0.3.0] — planned

- Web terminal (`docker exec` over WebSocket).
- Compose project view (containers grouped by project label).
- Engine switcher (Colima ↔ OrbStack ↔ Docker Desktop).
- MCP server (optional, for AI-agent control).

### [1.0.0] — planned

- Extracted to its own GitHub repo (`marvelousempire/dockyard`).
- Public release.
