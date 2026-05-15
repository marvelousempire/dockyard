> **Provenance:** Originally [plans/0012-dockyard-v0-and-plan-first-rule.md](https://github.com/marvelousempire/claude-chat-reader/blob/main/plans/0012-dockyard-v0-and-plan-first-rule.md)
> in marvelousempire/claude-chat-reader. Copied here Plan 0015/0016 so the
> Dockyard's standalone repo carries its full design history.

# Plan 0012 — Dockyard V0 build + plan-first workflow rule

## Context

Two threads converge here:

1. **Dockyard PRD shipped (Plan 0011)** — 741-line design doc, zero
   code. The post-ship gap+elevation audit identified 8 gaps and 8
   elevations. Marvin wants to swarm Claude Code subagents in parallel
   to implement V0 without git/process conflicts.

2. **Workflow gap** — every new Claude Code chat (or Cursor chat)
   forces Marvin to manually say "plan it first, save it to plans/,
   then execute." He wants this automatic. The existing user-global
   rule covers post-ship gap audits but not plan-first behavior. He
   also wants this to apply to Cursor.

This plan delivers both in one pass:
- **Track O** — the meta-rule that makes plan-first automatic for
  Claude Code + Cursor (cross-repo + project-tracked).
- **Tracks A–M** — Dockyard V0 implementation, file-isolated so
  multiple agents can run in parallel without stepping on each
  other.

The plan itself follows the very rule it installs (Track O), so the
audit trail starts here.

---

## Deliverables

### Deliverable 1 — Plan-first workflow rule (Track O, do FIRST)

Updates `CLAUDE.md` in two locations and adds matching Cursor rules so
every substantive change in any repo automatically enters plan mode,
uses Opus 4.7, writes a precise plan to `plans/NNNN-*.md`, and only
executes after approval.

**Files touched (4):**
- `/Users/nivram/.claude/CLAUDE.md` — user-global, append new section
- `/Users/nivram/Developer/claude-chat-reader/CLAUDE.md` — project,
  append new section
- `/Users/nivram/Developer/claude-chat-reader/.cursor/rules/plan-first.mdc`
  — project Cursor rule (new file, git-tracked)
- `/Users/nivram/.cursor/rules/plan-first.mdc` — user-global Cursor
  rule (new file)

**Exact rule text to install (verbatim, in all four files — adapt
header level for project vs. user-global):**

```markdown
## Plan-first for substantive changes — automatic plan mode

**When this fires:** the user asks for a change that touches more than
~2 files, adds a new feature / subsystem / sub-app, changes
architecture, modifies behavior other code depends on, or could
reasonably affect >50 lines. Not for typos, doc tweaks, single-file
bug fixes, questions, or explanations.

**What I do, without being asked:**

1. **Enter plan mode immediately.** Claude Code: call `EnterPlanMode`.
   Cursor: announce "I'll plan this first" and write to `plans/`
   before any edit.

2. **Switch to the most capable model** — Opus 4.7
   (`claude-opus-4-7`) — for plan writing. If currently on Sonnet or
   Haiku, suggest the user switch before proceeding.

3. **Explore read-only.** Claude Code: launch up to 3 Explore agents
   in parallel. Cursor: use read-only Read/Grep tools. Look for
   reusable code before proposing new code.

4. **Write a plan document** with these MANDATORY sections:
   - **Context** — why this change; what prompted it; intended
     outcome.
   - **Tasks (precise todos)** — numbered. Each task: literal
     what-to-do (file paths, function names, exact change), files
     touched, dependencies on other tasks, owner-agent suggestion
     (which subagent to assign).
   - **Critical files** — every path created or modified.
   - **Verification** — how to know it's done correctly: what to see,
     what commands to run, what tests pass. Include the **literal
     command** and the **expected output**.
   - **Out of scope** — what is intentionally NOT being done.

5. **Save the plan to** `plans/NNNN-snake-case-title.md` where NNNN
   is the next zero-padded integer (look at existing `plans/`
   folder).

6. **Request approval.** Claude Code: call `ExitPlanMode`. Cursor:
   print "Plan written — approve to proceed."

7. **Wait for explicit approval.** Do NOT begin implementation until
   the user says "go," "approved," "ship it," or similar.

**What this is not:** padding small work. If the request is a
single-file change or a question, just do it / answer it. The rule
fires for substantive scope, not every interaction.

**Where the plan goes:** every plan lands in `plans/NNNN-…md` in the
repo's plan folder before any code is written. Git-tracked,
append-only, numbered. This is the audit trail.
```

**Track O verification:**
- Open a NEW Claude Code chat in `claude-chat-reader/` → ask "add a
  metrics page that pulls from /api/usage" → assistant enters plan
  mode without being asked, writes `plans/0013-*.md`.
- Open a NEW Cursor chat in same repo → same request → Cursor
  announces it will plan first and writes `plans/0013-*.md` before any
  edit.
- Open Claude Code in an unrelated repo → same request → still enters
  plan mode (user-global rule fires).

---

### Deliverable 2 — Dockyard V0 (Tracks A–M)

Maps to the Dockyard PRD's P0 requirements. Each track is
**file-isolated** — no two tracks edit the same file, so the swarm
can't conflict. Coordination points are explicit.

#### Layer / dependency graph

```
Layer 1 (parallel — no deps):
  O  — workflow rule
  C  — socket detection
  L  — Caddy snippet
  M  — case study doc

Layer 2 (parallel — after Layer 1):
  A  — server core            (depends on C)
  B  — web UI skeleton        (no live data yet)
  K  — Linux/WSL paths + docs (depends on C)

Layer 3 (parallel — after Layer 2):
  D  — make doctor            (needs A + C)
  E  — MCP server             (needs A)
  F  — /health integration    (needs A)
  G  — compose project view   (needs A + B)
  H  — disk usage explorer    (needs A + B)
  I  — web terminal exec      (needs A + B)
  J  — tests                  (needs A + C)
```

#### Tracks

**Track A — Server core (Python stdlib)**
- Owner: `ruflo-core:coder`
- Files: `dockyard/server.py` (single file, ~600 lines)
- Deps: Track C
- What:
  - `http.server.HTTPServer` on port from `dockyard.config.json`
  - Custom `http.client.HTTPConnection` subclass that talks Unix
    socket via `socket.AF_UNIX`
  - Routes (proxy / wrap Docker Engine API):
    - `GET /api/containers` → `GET /containers/json?all=1`
    - `POST /api/containers/{id}/start|stop|restart`
    - `DELETE /api/containers/{id}?force=1`
    - `GET /api/containers/{id}/logs?follow=1` (chunked stream)
    - `GET /api/containers/{id}/stats` (chunked stream)
    - `GET /api/images` → `GET /images/json`
    - `POST /api/images/pull?from=nginx&tag=latest`
    - `DELETE /api/images/{id}`
    - `GET /api/volumes`, `GET /api/networks`, `GET /api/system`
    - `GET /api/system/df` → `GET /system/df`
    - `GET /` → serve `web/index.html`
    - `GET /static/*` → serve `web/static/*`
- Verification:
  ```bash
  cd dockyard && python server.py &
  curl -s http://localhost:4321/api/containers | head -c 200
  # expect: JSON array of containers (or [] if none running)
  curl -s http://localhost:4321/api/system | jq .ServerVersion
  # expect: version string like "28.5.1"
  ```

**Track B — Web UI skeleton**
- Owner: `ruflo-core:coder`
- Files: `dockyard/web/index.html` (single file, ~800 lines)
- Deps: none for skeleton; pulls data from Track A once both done
- What:
  - Tailwind CDN + vanilla JS (no build step)
  - Sidebar: Containers, Images, Volumes, Networks, Disk, Settings
  - Containers view: grouped by `Labels["com.docker.compose.project"]`
    by default (Track G), flat "All" fallback
  - Each container card: name, status pill, ports, image, age,
    actions (Start/Stop/Restart/Logs/Shell/Remove)
  - Logs panel: slide-over with auto-scrolling tail
  - Auto/Light/Dark theme toggle (reuse pattern from main app)
- Verification:
  - `open dockyard/web/index.html` in browser → renders skeleton with
    stub data; all P0 views are clickable.
  - With Track A running: views populate from API.

**Track C — Docker socket detection**
- Owner: `ruflo-core:coder`
- Files: `dockyard/lib/socket.py`, `dockyard/dockyard.config.json`
- Deps: none
- What:
  - `detect_socket()` function — probes in order:
    1. `DOCKER_HOST` env var
    2. `~/.colima/default/docker.sock`
    3. `~/.colima/<profile>/docker.sock` (iterate)
    4. `~/.orbstack/run/docker.sock`
    5. `~/Library/Containers/com.docker.docker/Data/docker.raw.sock`
    6. `/var/run/docker.sock` (Linux native)
  - Returns `(path, engine_type)` — engine_type ∈ {colima, orbstack,
    docker-desktop, native, env}
  - `dockyard.config.json` schema:
    ```json
    {
      "port": 4321,
      "socket": "auto",
      "auth": { "mode": "none" },
      "branding": { "name": "Dockyard", "accent": "#0E7C66" }
    }
    ```
- Verification:
  ```bash
  python -m dockyard.lib.socket detect
  # expect: /Users/nivram/.colima/default/docker.sock (engine: colima)
  ```

**Track D — Make doctor**
- Owner: `ruflo-core:coder`
- Files: `dockyard/Makefile`, `dockyard/scripts/doctor.sh`
- Deps: A, C
- What:
  - `make doctor` checks:
    - Python 3.10+ present
    - Colima installed (`command -v colima`)
    - Colima running (`colima status`) — if not, prompt to start
    - Socket reachable (`curl --unix-socket $SOCK http://x/_ping`)
    - Engine version (`/version` endpoint)
  - Auto-fix where safe: start Colima if installed-but-stopped (with
    user confirm); clean stale sockets
- Verification:
  ```bash
  make -C dockyard doctor
  # expect: all checks green; engine: colima 0.x.x; socket OK
  ```

**Track E — MCP server (AI-first from V0)**
- Owner: `ruflo-core:coder`
- Files: `dockyard/mcp.py` (single file)
- Deps: A
- What: MCP stdio server exposing 12 tools:
  - `list_containers(all=false)`, `start_container(id)`,
    `stop_container(id)`, `restart_container(id)`,
    `remove_container(id)`, `tail_logs(id, lines=100)`,
    `list_images()`, `pull_image(name)`, `remove_image(id)`,
    `list_volumes()`, `list_networks()`, `system_info()`
- Verification:
  ```bash
  pnpm dispatch "list my running containers"
  # expect: dispatcher routes via MCP, returns container list as text
  ```

**Track F — /health page integration**
- Owner: `ruflo-core:coder`
- Files: `src/app/health/page.tsx`, `src/lib/docker-health.ts`
- Deps: A
- What:
  - New `dockerHealth()` helper hits `localhost:4321/api/system`,
    returns `{ reachable, engine, version }`
  - `/health` adds a "Dockyard" row pill (green = reachable, gray
    = not started)
- Verification:
  - Visit http://localhost:3000/health → "Dockyard: reachable | engine:
    colima 0.x.x" row visible

**Track G — Compose project view (default landing)**
- Owner: same agent as Track B (coordinate file edits)
- Files: `dockyard/web/index.html` (Track B file)
- Deps: A, B
- What: group containers by `Labels["com.docker.compose.project"]`;
  show project pill colors; "All containers" view as secondary tab.
- Verification: with two compose projects running, landing page shows
  two groups with project labels.

**Track H — Disk usage explorer**
- Owner: `ruflo-core:coder`
- Files:
  - `dockyard/server.py` (add `/api/system/df` route — coordinate
    with Track A owner)
  - `dockyard/web/index.html` (add "Disk" tab — coordinate with
    Track B owner)
- Deps: A, B
- What: per-image / per-volume / per-build-cache size table; one-click
  `docker system prune` with confirm modal.
- Verification: open Disk tab → totals match `docker system df`.

**Track I — Web terminal exec**
- Owner: `ruflo-core:coder`
- Files:
  - `dockyard/server.py` (add WS handshake handler — coordinate
    with Track A owner)
  - `dockyard/web/index.html` (xterm.js — coordinate with Track B
    owner)
- Deps: A, B
- What: WebSocket handshake (RFC 6455) → `docker exec` proxy via
  hijacked TCP. xterm.js in browser.
- Verification: click container → Shell → working `sh -c "ls && uname"`.

**Track J — Tests**
- Owner: `ruflo-core:coder`
- Files:
  - `dockyard/tests/test_socket.py` (unit, mock filesystem)
  - `dockyard/tests/test_endpoints.py` (integration, real Docker)
  - `dockyard/Makefile` (add `make test` target — coordinate with
    Track D owner)
- Deps: A, C
- What:
  - Unit: socket detection with mocked `~/`
  - Integration: spin up nginx container; verify list/start/stop/remove
- Verification:
  ```bash
  make -C dockyard test
  # expect: pytest exits 0, all green
  ```

**Track K — Linux/WSL paths + docs**
- Owner: `ruflo-core:coder`
- Files:
  - `dockyard/lib/socket.py` (Track C file — coordinate)
  - `dockyard/PRD.md` (append "Platform support" subsection)
- Deps: C
- What: ensure `/var/run/docker.sock` detection works on Linux;
  document WSL2 path for Windows users.
- Verification: socket-detect unit tests cover Linux path; docs read
  cleanly.

**Track L — Caddy snippet**
- Owner: `ruflo-core:coder`
- Files: `dockyard/dockyard.caddyfile`
- Deps: none
- What: drop-in Caddyfile snippet routing `dockyard.localhost` →
  port 4321 with `tls internal`.
- Verification:
  ```bash
  caddy validate --config dockyard/dockyard.caddyfile
  # expect: valid config
  ```

**Track M — Case study doc**
- Owner: `ruflo-core:coder`
- Files: `dockyard/docs/case-study.md`
- Deps: none
- What: "The Clinic pattern, applied a third time" — short essay
  (~600 words) reinforcing the BLUEPRINT thesis: own folder, own
  PRD, Python stdlib server + single HTML UI, eventual repo
  extraction.
- Verification: file exists; reads clean; links work.

**Track N — Webhook outbox** — DEFERRED to V1 (out of scope here).

---

## Critical files

### New (15)
- `/Users/nivram/Developer/claude-chat-reader/.cursor/rules/plan-first.mdc`
- `/Users/nivram/.cursor/rules/plan-first.mdc`
- `dockyard/server.py`
- `dockyard/web/index.html`
- `dockyard/lib/socket.py`
- `dockyard/lib/__init__.py`
- `dockyard/dockyard.config.json`
- `dockyard/Makefile`
- `dockyard/scripts/doctor.sh`
- `dockyard/mcp.py`
- `dockyard/tests/test_socket.py`
- `dockyard/tests/test_endpoints.py`
- `dockyard/dockyard.caddyfile`
- `dockyard/docs/case-study.md`
- `src/lib/docker-health.ts`

### Modified (4)
- `/Users/nivram/.claude/CLAUDE.md` (append "Plan-first" section)
- `/Users/nivram/Developer/claude-chat-reader/CLAUDE.md` (append
  "Plan-first" section)
- `src/app/health/page.tsx` (add Dockyard row)
- `dockyard/PRD.md` (append "Platform support" subsection — Track K)

### Reused (don't recreate)
- `clinic/server.py` — Python stdlib HTTP server template
- `clinic/web/index.html` — single-file UI template
- `clinic/Makefile` — convenience-targets pattern
- `src/lib/agent.ts` — tool-loop pattern for MCP
- `src/scripts/dispatch-cli.ts` — `pnpm dispatch` routing
- Existing user-global gap-audit rule in `~/.claude/CLAUDE.md` —
  follow the same section/header style

---

## Verification (end-to-end checklist)

Run after all tracks land. Each numbered item maps to a track.

1. **Track O — workflow rule fires automatically**
   ```
   Open new Claude Code chat in claude-chat-reader/
   Ask: "add a metrics page that pulls /api/usage and renders charts"
   Expect: assistant enters plan mode without prompting, writes
           plans/0013-*.md, calls ExitPlanMode
   ```

2. **Track O — Cursor variant**
   ```
   Open Cursor in same repo
   Same request
   Expect: writes plans/0013-*.md before any edit
   ```

3. **Track A — server alive**
   ```bash
   make -C dockyard run &
   curl -s http://localhost:4321/api/containers | jq 'length'
   # expect: 0 (or count of running containers)
   ```

4. **Tracks B + G — UI with compose grouping**
   ```
   docker compose -f docker-compose.yml up -d
   open http://localhost:4321
   Expect: containers grouped under "claude-chat-reader" project pill
   ```

5. **Track A + B — logs streaming**
   ```
   Click any container → Logs
   Expect: tail streams, auto-scrolls, no console errors
   ```

6. **Track I — web terminal**
   ```
   Click container → Shell → type "uname -a" + Enter
   Expect: Linux response
   ```

7. **Track H — disk usage**
   ```
   Click Disk tab; compare to: docker system df
   Expect: totals match within rounding
   ```

8. **Track F — /health pill**
   ```
   open http://localhost:3000/health
   Expect: "Dockyard: reachable | engine: colima 0.x.x" row, green
   ```

9. **Track J — tests pass**
   ```bash
   make -C dockyard test
   # expect: pytest exits 0
   ```

10. **Track D — doctor green**
    ```bash
    make -C dockyard doctor
    # expect: ✅ Python 3.10+, ✅ Colima running, ✅ socket OK
    ```

11. **Track E — MCP wired**
    ```bash
    pnpm dispatch "list running containers"
    # expect: text list, routed through MCP tool
    ```

12. **Track L — Caddyfile valid**
    ```bash
    caddy validate --config dockyard/dockyard.caddyfile
    # expect: valid
    ```

13. **Track C — socket detect**
    ```bash
    python -m dockyard.lib.socket detect
    # expect: /Users/nivram/.colima/default/docker.sock (colima)
    ```

14. **Track M — case study reads clean**
    ```bash
    test -s dockyard/docs/case-study.md && wc -l dockyard/docs/case-study.md
    # expect: >100 lines, file non-empty
    ```

15. **Final — clean git state**
    ```bash
    git log --oneline -5
    # expect: 0012 commit(s) on top of 0011
    git status -s
    # expect: empty
    ```

---

## Out of scope (this plan)

- Webhook outbox for container events (Track N — V1)
- Multi-engine switcher UI (V1)
- Image-build UI (V2)
- Swarm / K8s management (V2+)
- Registry browsing (V1)
- Resource-limit adjustment (V1)
- Extracting Dockyard to its own GitHub repo (defer to post-V0)

---

## Execution order

1. Approve this plan via `ExitPlanMode`.
2. Copy plan body to `plans/0012-dockyard-v0-and-plan-first-rule.md`
   (git-tracked).
3. **Spawn Track O first** (workflow rule) — once it lands, every
   subsequent agent inherits plan-first behavior.
4. **Layer 1 in parallel** — Tracks C, L, M as background agents
   (foreground review when each completes).
5. **Layer 2 in parallel** — Tracks A, B, K once Layer 1 done.
   These are the heaviest tracks.
6. **Layer 3 in parallel** — Tracks D, E, F, G, H, I, J once Layer 2
   done. Tracks G/H/I require coordinating with the Track A and B
   owner so file edits don't conflict (use `ruflo-core:reviewer`
   between each track to merge cleanly).
7. **Final reviewer pass** — `ruflo-core:reviewer` audits everything.
8. **Commit + push** as plan 0012. Single squash-commit or one commit
   per layer — Marvin's call.
9. **Run full verification checklist** (above).
10. **Tag** `dockyard-v0.2.0` (per CHANGELOG roadmap).

Estimated effort:
- Track O (workflow rule): 20 min
- Layer 1 (C, L, M): 1 hour combined
- Layer 2 (A, B, K): 3–4 hours combined (heaviest)
- Layer 3 (D, E, F, G, H, I, J): 2–3 hours combined
- Verification + commit: 30 min
- **Total: ~7–9 hours focused, parallelizable across ~4 agents to
  ~3 hours wall-clock.**

---

## Why this plan structure

- **File isolation** between tracks means parallel agents don't
  conflict. The only shared files are `dockyard/server.py` and
  `dockyard/web/index.html` — and we mark those tracks (G/H/I)
  explicitly as "coordinate with Track A/B owner" so the reviewer
  agent can sequence them.
- **Layered dependencies** instead of one linear chain — gives the
  swarm something to chew on at every stage.
- **Verification is literal** — each item has a command and an
  expected output, so an agent (or Marvin) can run the checklist
  blind.
- **Track O ships first** — the workflow rule is independent and
  applies immediately, so every track that follows inherits the
  "plan-first" discipline.
- **Reuses existing patterns** — Clinic server/UI shape, dispatcher
  routing, gap-audit rule style — so this isn't inventing new
  conventions; it's extending proven ones.
