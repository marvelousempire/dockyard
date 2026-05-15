> **Provenance:** Originally [plans/0011-colima-decision-and-dockyard-app.md](https://github.com/marvelousempire/claude-chat-reader/blob/main/plans/0011-colima-decision-and-dockyard-app.md)
> in marvelousempire/claude-chat-reader. Copied here Plan 0015/0016 so the
> Dockyard's standalone repo carries its full design history.

# Plan 0011 — Colima decision record + Dockyard (lightweight Docker manager UI)

**Date:** 2026-05-14
**Status:** Shipped (PRD-only phase)
**Author:** Marvin + Claude

## Context

Two things converged this week:

1. **Docker Desktop has been failing repeatedly** on this Apple Silicon
   Mac running macOS Tahoe (26.3.1). Symptom: "Docker Desktop is unable
   to start" dialog, stuck `com.docker.backend` processes, broken
   sockets, full session blocked. We worked around it by killing
   processes and clearing stale vsock files, but the fix never held —
   it crashed again on every next start. Root cause: Docker Desktop
   4.70.0 has compatibility issues with macOS Tahoe + Apple Silicon,
   plus subscription / license check noise, plus 200 GB+ VM disk
   overhead.

2. **The solution turned out to be Colima** — a native Apple Silicon
   Docker runtime that provides the exact same `docker` socket the CLI
   uses, without Docker Desktop's Electron UI, license prompts, or
   compatibility regressions.

Marvin wants two deliverables out of this:

- **(A)** A PRD that captures, in plain English, *why* we're moving to
  Colima. Decision record. Future contributors (and future-me) should
  be able to read this and understand exactly why we made this choice
  and what trade-offs were considered.
- **(B)** A proposal, attached to that PRD, for building a lightweight
  Docker Desktop replacement UI — container / image / volume / network
  management without the bloat. Same philosophy as the Clinic:
  self-contained sub-app in its own folder, eventually its own GitHub
  repo. **Folder name: `dockyard/`** (chosen via AskUserQuestion).

This plan is the audit-trail entry for both deliverables.

## Approach

Single PRD document with two parts, sitting in a new `dockyard/` folder
that becomes the seed for the future sub-app. Mirror the Clinic's file
convention so the folder is ready to grow.

### A. Folder structure created

```
dockyard/
├── README.md           # 5-second pitch + status + folder roadmap
├── PRD.md              # THE document — why Colima + Dockyard proposal
├── CHANGELOG.md        # version history (v0.1.0 — pre-build)
└── LICENSE             # MIT (mirrored from clinic/LICENSE)
```

Server, web UI, Makefile, schema files come in a follow-up plan once
the design is locked.

### B. The PRD document — outline

**Part 1: Why Colima instead of Docker Desktop**

1. Executive summary
2. The problem we hit (specific, dated, real — Docker Desktop 4.70.0 on
   macOS Tahoe 26.3.1)
3. What Docker Desktop actually is, technically (Electron UI on top of
   `qemu` / Apple VirtualizationKit VM running Linux + dockerd)
4. What Colima is — exact equivalent at the socket layer (Lima VM +
   dockerd; same `~/.colima/default/docker.sock`)
5. Why "exact equivalent" matters — zero workflow change
6. What changes for the user (table: `Open Docker Desktop` →
   `colima start`; everything else unchanged)
7. Trade-offs we considered (Docker Desktop, Colima, OrbStack, Podman)
8. Why Colima won (native Apple Silicon, no UI overhead, free for
   commercial use, no license prompts, drop-in compatible)
9. What we lose by moving — the GUI (addressed by Part 2)
10. Migration playbook (one-time chained command)

**Part 2: Dockyard — lightweight Docker manager UI**

11. The proposal
12. Personas (Marvin, Olivia, Liam, Claude-as-agent)
13. Design constraints — "without the bloat":
    - Zero pip install / zero npm install for the server (Python 3
      stdlib only)
    - Pre-built single-file HTML web UI (Tailwind CDN)
    - Optional Vite + React rebuild path
    - < 50 MB total install (vs Docker Desktop's ~1.5 GB)
    - Works with any Docker socket (Colima, Docker Desktop, OrbStack,
      remote daemons)
14. Functional requirements (P0):
    - Container list, start / stop / restart / remove
    - Streaming logs
    - Web terminal (`docker exec`)
    - Image list, pull, remove
    - Volume + network list and inspect
    - Live resource stats per container
    - Compose project view (grouped by project label)
15. Functional requirements (P1):
    - Pause / unpause / rename
    - Env-var edit + restart
    - Resource-limit adjustment
    - Image-pull progress
    - Registry browsing
    - Multi-engine switcher (Colima ↔ OrbStack ↔ Docker Desktop)
16. Out of scope: Swarm / K8s, image building, marketplace, sign-in
17. Architecture (mirrors Clinic):
    - `dockyard/server.py` — Python 3 stdlib HTTP server, hits Docker
      socket via `http.client.HTTPConnection` with custom unix-socket
      override
    - `dockyard/web/index.html` — vanilla JS + Tailwind CDN, one file
    - `dockyard/dockyard.config.json` — port, socket, auth mode,
      branding
    - `dockyard/Makefile` — `make run`, `make ui`, `make doctor`
    - Optional Node CLI / MCP server for AI agent control
18. The Docker Engine API surface to wrap (list of endpoints)
19. Web UI mockup (ASCII)
20. Configuration schema (`dockyard.config.json`)
21. MCP server (P1, for AI-agent control)
22. Non-functional requirements (performance, security, reliability,
    portability)
23. Success metrics
24. Distribution path (V0 in this repo → V1 stabilize → V2 extract to
    its own GitHub repo)
25. Build philosophy alignment with the BLUEPRINT

### C. The README.md

Short — < 100 lines. Sections:
- What Dockyard is (one paragraph)
- Status: "Pre-build — see PRD.md for the design"
- 5-second pitch: "Docker Desktop minus the bloat"
- What you'll get (P0)
- Folder roadmap
- Why it lives in claude-chat-reader/ for now
- Read next

### D. The CHANGELOG.md

```markdown
## [0.1.0] — 2026-05-14
### Born
- PRD written, README seeded, LICENSE mirrored.
- Pre-build phase. Implementation starts at v0.2.0.
```

## Critical files

### New
- `dockyard/README.md`
- `dockyard/PRD.md` (~500 lines, the main deliverable)
- `dockyard/CHANGELOG.md`
- `dockyard/LICENSE` (MIT, copied from `clinic/LICENSE`)
- `plans/0011-colima-decision-and-dockyard-app.md` (this file)

### Reused patterns
- `clinic/` folder structure — exact template
- `clinic/PRD.md` — section structure
- `clinic/server.py` — Python 3 stdlib server template (documented in
  Dockyard PRD, not yet built)
- `clinic/web/index.html` — single-file UI template (also documented,
  not yet built)
- `clinic/Makefile` — convenience-targets pattern
- `BLUEPRINT.md` — overall stack pattern

## Verification

- [x] `dockyard/` folder exists at repo root with four files
- [x] `dockyard/PRD.md` reads cleanly end-to-end — non-technical reader
      can understand Part 1; engineer can scope from Part 2
- [x] `dockyard/README.md` is scannable in 30 seconds
- [x] `plans/0011-*.md` mirrors the PRD intent
- [ ] `git log --oneline -3` shows a clean commit (pending)
- [ ] `git status -s` empty after commit + push (pending)
- [ ] GitHub renders both PRD.md and README.md correctly (pending)

## Out of scope (this plan)

- Building `server.py` or `web/index.html` — that's the next plan
  (likely 0012)
- Choosing exact UI framework for the rebuild path (Vite + React vs.
  Svelte vs. Preact — defer)
- Auth model details (token vs. OAuth vs. none — defer)
- The actual extraction to its own GitHub repo — same pattern as the
  Clinic, can happen when V0 ships

## Execution order

1. ✅ Create `dockyard/` directory
2. ✅ Write `dockyard/PRD.md` (the main deliverable — comprehensive)
3. ✅ Write `dockyard/README.md` (concise)
4. ✅ Write `dockyard/CHANGELOG.md` (one entry)
5. ✅ Copy `clinic/LICENSE` → `dockyard/LICENSE`
6. ✅ Write this plan
7. `git add dockyard/ plans/0011-*.md`
8. Commit: "plan 0011 — Colima decision recorded, Dockyard PRD seeded"
9. `git push`
10. Verify on GitHub

## Follow-up (next plan)

**Plan 0012 — Dockyard V0 build**
- `dockyard/server.py` — Python 3 stdlib server, Docker socket adapter
- `dockyard/web/index.html` — single-file UI with the P0 feature set
- `dockyard/dockyard.config.json` — example config
- `dockyard/Makefile` — `make run`, `make doctor`, `make ui`
- Wire `app.config.json` to point at Dockyard's port (default 4321)
- Caddy route in the main stack if the user wants HTTPS

Estimated effort for the V0 build: ~6–10 hours focused work.
