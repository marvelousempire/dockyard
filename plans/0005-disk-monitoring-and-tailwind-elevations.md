# Plan 0005 — Disk-monitoring + Tailwind v4 elevations

Status: drafted 2026-05-23. User approved the lettered elevation menu (A–H) from
the gap-audit pass on commits `8346702` (host disk monitoring) and `38fcee6`
(Tailwind v4 source).

## Context

Two recent ships landed with real gaps:

1. **`38fcee6` shipped Tailwind v4 source + `bin/tw` standalone CLI shim** —
   but the HTML at `web/index.html:8` still loads `https://cdn.tailwindcss.com`.
   The new `@theme`, OKLCH colors, view-transitions, and `.panel/.v-card`
   components are present in `web/styles/input.css` but never reach the browser.
   Makefile has no `tw-build`/`tw-watch` targets despite the input.css header
   claiming they exist. The compile pipeline has never run end-to-end.

2. **`8346702` shipped `/api/host/disk` + a low-space header badge** —
   but the badge is a dead-end (text-only tooltip, no click), it monitors host
   `/` instead of the Docker volume that actually fills up, thresholds are
   magic numbers in JS, errors are swallowed, polling runs every 2s on the main
   refresh tick, and there are no tests.

The user picked the full lettered elevation menu (A–H) to close all of this
in one pass.

## Tasks

### A. Compile-on-boot in `bin/go` + wire compiled CSS

1. Add `compile_css()` step in `bin/go` that runs after engine detection but
   before launching the server. If `web/static/dockyard.css` is missing OR
   `web/styles/input.css` is newer, invoke `bin/tw -i web/styles/input.css -o
   web/static/dockyard.css` and report ok/warn. Don't fail boot if compile
   fails (warn + continue with CDN fallback) — the goal is to remove the CDN,
   but a working-degraded mode beats a hard-down.
2. In `web/index.html`:
   - Remove `<script src="https://cdn.tailwindcss.com">`.
   - Add `<link rel="stylesheet" href="/static/dockyard.css">`.
   - Move the inline `<style>` `@apply` rules (pill, btn, surface, nav-item,
     etc.) into `web/styles/input.css` under `@layer components`. The CDN was
     evaluating those at runtime; the standalone CLI evaluates them at build
     time.
   - Keep the small handful of CSS-variable–driven rules (`--dy-accent` runtime
     branding) inline since they're set by JS at config-load time.
3. Add `make tw-build` and `make tw-watch` targets to `Makefile`.
4. Add `web/static/dockyard.css` to `.gitignore` (built artifact; bin/go
   produces it on boot).

**Files:** `bin/go`, `web/index.html`, `web/styles/input.css`, `Makefile`,
`.gitignore`.

### B. Disk badge → one-click Dustpan modal

1. Make the low-space badge clickable. On click, open a modal showing:
   - Current disk state (host + Docker)
   - Two options: "Run `docker system prune`" (POST `/api/system/prune`,
     existing endpoint) and "Cancel."
2. After prune completes, refetch `/api/host/disk` + `/api/system/df` and show
   "Freed X MB."

**Files:** `web/index.html`.

### C. Monitor Docker volume too

1. Extend `_serve_host_disk` in `server.py`:
   - Keep host `/` reading.
   - Also query Docker `/info` for `DockerRootDir`, then `shutil.disk_usage`
     that path if it exists locally. (On Colima/macOS `DockerRootDir` is inside
     the VM — falls back to `null`.)
   - Also include Docker's own `LayersSize` from `/system/df` as a fallback
     "Docker storage in use" signal.
2. Response shape:
   ```json
   {
     "host": {"total": …, "used": …, "free": …, "percent_used": …},
     "docker_root": {"path": "…", "total": …, "used": …, "free": …,
                     "percent_used": …} | null,
     "docker_layers_bytes": 12345
   }
   ```
3. UI: badge logic considers whichever disk has the lower free%. Modal shows
   both.

**Files:** `server.py`, `web/index.html`.

### D. Disk-usage sparkline in header

1. Add `state.diskSeries = []` (array of `{t, percentUsed}`).
2. On each `loadHostDisk()` push the sample, trim to `state.sparkSeconds`.
3. Reuse `sparkPath()` to render a tiny inline SVG next to the disk badge
   (visible whenever badge is visible, i.e. when warning is active).
4. Use a new sparkline color class `.spark-disk` (rose/amber, threaded through
   `input.css`).

**Files:** `web/index.html`, `web/styles/input.css`.

### E. Time-to-full prediction

1. With `>= 4` samples spanning `>= 10s`, compute linear-regression slope
   of `free` over `t`. If slope is negative (filling up), project time-to-zero
   and surface it.
2. Badge label switches to `"⚠ full in ~12m"` (or `"⚠ 2.1% free"` if not
   filling). Modal shows both.
3. Implementation: simple least-squares; bail to flat-rate display if slope
   ≥ 0 or sample variance below a tiny epsilon.

**Files:** `web/index.html`.

### F. Config-driven thresholds

1. Add to `dockyard.config.json`:
   ```json
   "ui": {
     ...,
     "disk_warn_percent": 5,
     "disk_warn_mb": 500,
     "disk_warn_poll_seconds": 10
   }
   ```
2. Read in `loadConfig()` into `state.diskWarnPercent`, `state.diskWarnMb`,
   `state.diskPollMs`. Default to current magic numbers if missing.
3. Replace hardcoded `5` and `500` in the disk-warning render.
4. Use `state.diskPollMs` to drive disk polling on its own `setInterval`
   instead of the 2s `refresh()` tick.

**Files:** `dockyard.config.json`, `web/index.html`.

### G. Snapshot-on-warn

1. New `POST /api/host/disk/snapshot` server endpoint:
   - Write `/tmp/dockyard-disk-warn-<isoTs>.txt` with:
     - `df -h /` output (via `subprocess.run(["df", "-h", "/"])`)
     - `/system/df` from Docker (top 10 by size for images + volumes)
     - `/info` summary (engine, storage driver, DockerRootDir)
   - Return `{path: "/tmp/…", bytes: …}`.
2. UI: when threshold *first* trips this session (deduped via
   `state.diskWarnSnapshotTaken = false → true`), fire-and-forget POST the
   snapshot. Log path to console.

**Files:** `server.py`, `web/index.html`.

### H. Test `colima-hung` recovery + new endpoints

1. Add unit tests to `tests/test_endpoints.py`:
   - `test_host_disk_endpoint` — asserts `/api/host/disk` returns `host` block
     with sane numbers (under `TestServerOnly`, since `shutil` doesn't need
     Docker).
   - `test_host_disk_snapshot_writes_file` — POST `/api/host/disk/snapshot`,
     assert file exists and bytes > 0.
2. Add a tiny shell test `tests/test_bin_go_engine_detection.sh`:
   - Source `bin/go`'s `detect_engine` function.
   - Stub `colima` (zero exit) + `curl` (nonzero) on PATH → asserts
     `ENGINE=colima-hung`.
   - Stub both as ok → asserts `ENGINE=colima`.
3. Wire into `make test-unit` (script run via bash, exits non-zero on fail).

**Files:** `tests/test_endpoints.py`, `tests/test_bin_go_engine_detection.sh`
(new), `Makefile`.

## Critical files

Created:
- `tests/test_bin_go_engine_detection.sh`
- `plans/0005-disk-monitoring-and-tailwind-elevations.md`

Modified:
- `web/index.html`
- `web/styles/input.css`
- `server.py`
- `bin/go`
- `Makefile`
- `dockyard.config.json`
- `.gitignore`
- `tests/test_endpoints.py`

Built at boot (gitignored):
- `web/static/dockyard.css`

## Verification

After implementation, run each from the repo root:

```bash
# Tailwind compiles and is served
bin/tw -i web/styles/input.css -o web/static/dockyard.css
test -s web/static/dockyard.css && echo OK
# Expected: OK, file > 50KB

# HTML no longer loads CDN
! grep -q 'cdn.tailwindcss.com' web/index.html && echo OK
# Expected: OK

# Disk endpoint shape
make run &
sleep 1
curl -s http://127.0.0.1:4321/api/host/disk | python3 -m json.tool
# Expected: object with `host` block, `docker_root` block-or-null,
# `docker_layers_bytes` number

# Snapshot writes a file
curl -sX POST http://127.0.0.1:4321/api/host/disk/snapshot | python3 -m json.tool
ls -l /tmp/dockyard-disk-warn-*.txt | tail -1
# Expected: file path returned, file exists with non-zero size

# Tests pass
make test-unit
bash tests/test_bin_go_engine_detection.sh && echo OK
# Expected: all tests green, shell test prints OK

# UI smoke
make ui
# Expected: browser opens, header looks identical (Tailwind compiled),
# no console errors, no network request to cdn.tailwindcss.com.
```

## Out of scope

- Reworking Dustpan integration beyond wiring the modal to the existing
  `/api/system/prune`. A richer Dustpan flow (per-resource preview, dry-run,
  size-sorted lists) is a separate plan.
- Reverse-engineering Colima VM disk usage from outside the VM. We surface
  `DockerRootDir` if locally readable; the VM-internal case stays as
  `docker_root: null` with `docker_layers_bytes` carrying the signal.
- Refactoring the inline `<script>` blob into module files. Plan 0005 is
  scoped to the disk + Tailwind delta only.
- Adding a feature flag to keep the CDN around. We commit to the compiled
  pipeline; rollback is `git revert` if it bites.

## Approval

User approved elevation menu A–H on 2026-05-23 in response to the
gap-audit/elevation pass. This plan codifies that scope.
