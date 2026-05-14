# The Clinic pattern, applied a third time

How `claude-chat-reader` became the seed for a reusable BLUEPRINT, and
why **Dockyard** is the third sub-app to inherit it.

## The pattern (one paragraph)

A self-contained sub-app lives in its own folder at the repo root:
own `README.md`, own `PRD.md`, own `CHANGELOG.md`, own `LICENSE`.
Server is **Python 3 standard library only** — zero pip install, no
virtualenv. UI is a **single HTML file** that loads Tailwind from a
CDN and stays vanilla-JS. Configuration is **one JSON file** with
sensible defaults. A `Makefile` exposes three targets: `make run`,
`make doctor`, `make ui`. The whole thing is < 50 MB on disk and
boots in < 200 ms. When it matures, it gets extracted to its own
GitHub repo — same way the [Clinic](../../clinic/README.md) is on
that path.

## The three sub-apps so far

| # | Folder | Purpose | State |
|---|--------|---------|-------|
| 1 | `claude-chat-reader/` (root) | The original app: dashboard + RAG over Claude exports | Production |
| 2 | [`clinic/`](../../clinic/README.md) | Universal knowledge register — issues, ideas, plans, ledger, rules, definitions, features, laws | Production (V2 RAG embeddings shipped Plan 0010) |
| 3 | [`dockyard/`](../README.md) | Lightweight Docker manager UI (Docker Desktop replacement) | Pre-build (V0 in progress, Plan 0012) |

## Why repeat the pattern instead of inventing a new one

Three reasons, in order of importance:

### 1. Zero-install means the sub-app survives the next OS update

Docker Desktop crashed on macOS Tahoe 26.3.1 because of a
compatibility regression between Electron + qemu + the host
VirtualizationKit (see [Dockyard PRD § Why Colima](../PRD.md)). The
Clinic doesn't crash on OS updates because it has no native
dependencies — `python3 server.py` works on every Python 3.10+
install since forever. Dockyard inherits that survivability.

### 2. The mental model transfers — and so do the muscle memory commands

Once you know how to run the Clinic:

```bash
make -C clinic run         # starts on :7000
open http://localhost:7000
```

You already know how to run Dockyard:

```bash
make -C dockyard run       # starts on :4321
open http://localhost:4321
```

No new conventions to learn. The `clinic.config.json` and
`dockyard.config.json` schemas overlap so the customization steps are
identical: pick a port, pick a brand color, you're done.

### 3. Extraction to its own repo is a `git filter-repo` away

When the Clinic graduates from `claude-chat-reader/clinic/` to its own
GitHub repo, the move is one `git filter-repo --subdirectory-filter
clinic/` away — full commit history preserved. Same for Dockyard.
This pattern is **explicitly designed for eventual extraction**, which
is what makes the BLUEPRINT thesis hold: every sub-app you write here
is ~80% of a future portfolio of standalone tools.

## The BLUEPRINT manifest

These constraints are non-negotiable for any sub-app added under this
pattern (see [BLUEPRINT.md](../../BLUEPRINT.md)):

1. **Own folder** at the repo root. No nesting under `src/`.
2. **Own PRD** before any code. Plan-mode-first (rule installed Plan
   0012).
3. **Python 3 stdlib server** (or stdlib equivalent in another
   ecosystem). No build step required to start.
4. **Single HTML UI file** with Tailwind CDN. Optional Vite + React
   rebuild path documented but never required.
5. **One JSON config file** with defaults that work out of the box.
6. **Three Makefile targets** — `run`, `doctor`, `ui`.
7. **MIT licensed** (or compatible). Solo-friendly.
8. **Privacy-gated** if it talks to external networks (the existing
   `assertAllowed()` pattern from the main app).
9. **MCP-ready** — at least a stub `mcp.py` (or equivalent) so AI
   agents can drive the sub-app from day one. Bake in early; don't
   bolt on.
10. **Documented for extraction.** Every sub-app must be portable:
    its README explains how to copy/move it into another repo.

## What this case study is meant to do

If you're reading this six months from now and considering whether to
build a fourth sub-app under the same pattern: **yes, do it the same
way.** The BLUEPRINT is now battle-tested across three very different
domains — knowledge management (Clinic), runtime management
(Dockyard), and conversation archive (the main app). The third
instance is the one where you stop calling it a coincidence and start
calling it a pattern.

The fourth sub-app, when it lands, won't need new conventions. It'll
copy `dockyard/` (the cleanest of the three) as the starting point,
rename the config, swap the server logic, and ship.

## See also

- [`../PRD.md`](../PRD.md) — full Dockyard design
- [`../../clinic/PRD.md`](../../clinic/PRD.md) — Clinic design
- [`../../BLUEPRINT.md`](../../BLUEPRINT.md) — the underlying stack
  pattern
- [`../../plans/0008-app-blueprint-and-scaffold.md`](../../plans/0008-app-blueprint-and-scaffold.md)
  — when the BLUEPRINT became formal
- [`../../plans/0012-dockyard-v0-and-plan-first-rule.md`](../../plans/0012-dockyard-v0-and-plan-first-rule.md)
  — the plan that produced this case study
