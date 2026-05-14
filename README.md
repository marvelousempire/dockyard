# Dockyard

> **Docker Desktop minus the bloat.** A lightweight, local-first UI for
> managing containers, images, volumes, and networks — built to work with
> any Docker socket (Colima, OrbStack, Docker Desktop, remote daemons).

## Status

**V0 (v0.2.0) — runnable.** Server, UI, socket auto-detect, doctor,
MCP, tests, Caddyfile snippet — all shipped (Plan 0012). Web-terminal
exec deferred to v0.3.0. See **[PRD.md](./PRD.md)** for the design and
**[CHANGELOG.md](./CHANGELOG.md)** for what's in.

```bash
make -C dockyard doctor   # check engine + socket
make -C dockyard run      # start on :4321
open http://127.0.0.1:4321
```

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

## Why this exists in `claude-chat-reader/`

It's seeded here because (a) this repo is where the Colima decision was
made and documented, (b) the Clinic precedent shows the pattern works,
(c) Marvin already runs `claude-chat-reader` daily so the muscle memory
is here. Once V0 ships and stabilizes, Dockyard moves to its own repo.

## Read next

1. **[PRD.md](./PRD.md)** — the design and decision record
2. [../clinic/README.md](../clinic/README.md) — the pattern Dockyard
   follows
3. [../BLUEPRINT.md](../BLUEPRINT.md) — the stack template Dockyard
   plugs into

## License

MIT — see [LICENSE](./LICENSE).
