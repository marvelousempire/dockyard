# Dockyard — Product Requirements Document

**Classification:** Public  
**Version:** 0.1.0 (pre-build — design phase)  
**Date:** 2026-05-13  
**Status:** Approved — execution pending  
**Authors:** Marvin, Claude

---

# Part 1 — Why Colima instead of Docker Desktop

## Executive summary (plain English)

For the past several months, Docker Desktop has been getting harder to use
on Apple Silicon Macs running macOS Tahoe (26.x). It crashes on startup,
shows cryptic "Docker Desktop is unable to start" errors, holds onto stale
processes and sockets, eats 200+ GB of disk for its VM image, and pushes
license / subscription prompts in the way of work.

We hit this wall hard during the build of this project. After many resets,
we moved to **Colima** — an open-source Apple Silicon-native runtime that
does exactly what Docker Desktop does at the technical level (provides a
Docker socket), without any of the UI overhead or compatibility issues.

For day-to-day work, **nothing changes**. The exact same `docker compose
up`, `make go`, `docker ps`, and `docker logs` commands work identically.
The only difference is the startup command — `colima start` replaces
opening the Docker Desktop app. Everything else, from the `Dockerfile`
to the `docker-compose.yml`, stays the same.

What we lose by leaving Docker Desktop is the GUI for managing containers,
images, volumes, and networks. **Part 2 of this document proposes a
lightweight replacement for that GUI — Dockyard.**

---

## What happened today (the specific motivating incident)

On 13 May 2026, during a build session, Docker Desktop entered a broken
state on this Mac (Apple M1, macOS Tahoe 26.3.1, Docker Desktop 4.70.0).
The symptoms were:

- **Startup fails repeatedly.** The Docker Desktop UI opens, shows an
  "Unable to start" error dialog, then sits there. The whale icon never
  goes solid.
- **The backend process gets stuck.** `pgrep -f com.docker.backend`
  returns a PID. The process is running but unresponsive — it doesn't
  answer requests on its own socket.
- **Stale sockets block restart.** When you kill Docker Desktop and try
  again, leftover vsock files at
  `~/Library/Containers/com.docker.docker/Data/vms/0/*.sock` make it
  think a VM is already running. It refuses to start a new one.
- **The CLI hangs.** Every `docker` command hangs for 30+ seconds and
  eventually returns a 503 — the Docker daemon's API is responding but
  in an error state.
- **The VM image is 228 GB.** The `Docker.raw` virtual disk has grown to
  228 GB even though we have nothing close to that volume of data —
  Docker Desktop's storage management has bloat.
- **Plugin layer adds its own failure mode.** A stale `docker-ai` CLI
  plugin in `~/.docker/cli-plugins/` was independently blocking every
  `docker` invocation, waiting on metadata fetch that never returned.

After multiple resets, kills, and socket cleanups, the state never held.
The fundamental problem: **Docker Desktop 4.70.0 has compatibility
regressions on macOS Tahoe + Apple Silicon that no amount of workaround
clears.**

---

## What Docker Desktop actually is, technically

This part matters for understanding why Colima is a viable replacement.

Docker Desktop is **three things stacked together**:

1. **A Linux VM** running on top of macOS's virtualization framework.
   This VM hosts the actual Docker daemon (`dockerd`). It's where your
   containers actually run. Container code is Linux code; macOS itself
   cannot run Linux containers natively.

2. **A daemon socket** at `~/.docker/run/docker.sock`. This is a Unix
   domain socket that the `docker` CLI talks to. Every `docker ps`,
   `docker compose up`, `docker logs`, and `make go` command in this
   repo writes to this socket. The socket is the actual API.

3. **An Electron-based GUI** that wraps the above with a menu bar app,
   a settings panel, container management screens, an image registry
   browser, an extensions marketplace, license / subscription prompts,
   telemetry, update notifications, and more.

The CLI only needs #1 and #2 — the VM and the socket. The whole GUI
(#3) is optional overhead. Docker Desktop bundles them all together
because it's a commercial product that wants you to think of it as one
thing.

---

## What Colima actually is, technically

Colima ("**Co**ntainers on **Lima**") is exactly the first two pieces
without the third:

1. **A Linux VM** running on top of macOS's virtualization framework
   (the same `Virtualization.framework` that Docker Desktop now uses).
   Hosted on top of Lima, an open-source Linux-VM-on-Mac project.

2. **A daemon socket** at `~/.colima/default/docker.sock` (and
   symlinked to `~/.docker/run/docker.sock` for compatibility). Same
   wire protocol, same API, same behaviour.

3. **No GUI.** That's the whole point. It runs in the background. You
   start it with `colima start`. You stop it with `colima stop`. That's
   the entire user interface.

For the `docker` CLI — and for `docker compose`, `make go`, and every
single command in this repo's `Makefile` — Colima is **indistinguishable
from Docker Desktop**. The CLI doesn't know or care which one is
behind the socket. The wire protocol is the Docker Engine API, which is
versioned and stable. Both Docker Desktop and Colima implement it.

---

## Why "exact equivalent at the socket layer" matters

The key technical claim: anything that talks to the Docker socket talks
to it the same way regardless of who's listening on the other end.
This includes:

- The `docker` CLI itself
- `docker compose` (a separate binary that calls the daemon API)
- `docker buildx`
- Our `Dockerfile` (interpreted by `dockerd` inside the VM)
- Our `docker-compose.yml` (interpreted by `docker compose`)
- All tooling that uses the Docker API: Testcontainers, `docker-py`,
  CI runners, IDE integrations
- The Caddy container, Postgres containers, watcher container, Metabase
  container — none of them know or care

When we switch the listener from Docker Desktop to Colima, **everything
above keeps working unchanged**.

This is the difference between Colima and other alternatives like
podman (which has a Docker-compatible API but isn't byte-for-byte
identical) or OrbStack (which is also a Docker socket but a closed
source commercial product).

---

## What changes for the user

In practical, day-to-day terms:

| Before (Docker Desktop) | After (Colima) |
|---|---|
| Open Docker Desktop app | Run `colima start` in terminal |
| Whale icon in menu bar | No icon — runs invisibly |
| Periodic "update available" prompts | Pull updates manually with `brew upgrade colima` |
| Settings panel for resource limits | `colima start --cpu 4 --memory 8 --disk 60` |
| Built-in container/image GUI | **Lost** (Dockyard, Part 2, recovers this) |
| ~1.5 GB application | ~50 MB binary + the VM image |
| 200 GB+ VM disk | Configurable; defaults to 60 GB |
| License prompts (for some users) | None — Apache 2.0 |
| Subscription required for commercial use ($) | Free for commercial use |

Everything else — `make go`, `docker compose up`, `docker ps`,
`docker logs`, `docker exec`, `docker pull`, `docker build` — is
**byte-for-byte identical**. Your `docker-compose.yml` doesn't change.
Your `Dockerfile` doesn't change. The `Makefile` doesn't change.

---

## Trade-offs we considered

Four runtimes evaluated:

### Docker Desktop (incumbent)
**Pros**
- Familiar GUI for less technical users
- One-click install
- Built-in extensions marketplace
- Auto-update mechanism

**Cons**
- Crashing repeatedly on macOS Tahoe + Apple Silicon
- ~1.5 GB app + 200+ GB VM disk
- License required for commercial use at >250-employee orgs
- Subscription prompts in the UI
- Telemetry on by default
- Electron-based GUI consumes meaningful RAM even when idle

### Colima (chosen)
**Pros**
- Open source (Apache 2.0)
- Native Apple Silicon support — no Rosetta, no x86 translation
- Drop-in compatible with `docker` CLI
- No GUI overhead
- Free for any use, including commercial
- Tiny memory footprint when idle
- Lima underneath is well-maintained and trusted

**Cons**
- No GUI for managing containers / images
  → **This document's Part 2 addresses this**
- Slightly more terminal-driven setup (one command)
- Update mechanism is manual (`brew upgrade`)

### OrbStack
**Pros**
- Native Apple Silicon, very fast
- Has a GUI
- Drop-in Docker socket

**Cons**
- Closed source, commercial product
- Free tier is for personal use only — would need a paid plan for our
  long-term use
- Lock-in risk (closed source)
- Less control over the underlying VM

### Podman
**Pros**
- Daemonless (security advantage in some setups)
- Open source (Apache 2.0)
- Increasing Docker compatibility

**Cons**
- Not byte-for-byte API compatible — small differences cause subtle
  bugs in tooling
- `podman-compose` is not a perfect drop-in for `docker compose`
- Less mature on macOS than on Linux

### Conclusion

Colima is the right choice. It's exactly Docker Desktop minus the
parts we don't need. The cost — losing the GUI — is recovered by
building Dockyard (Part 2), which we wanted to build anyway as
a self-contained lightweight tool.

---

## Migration playbook (one-time setup)

The full migration is one chained command:

```bash
sudo chown -R "$(whoami)" /opt/homebrew && \
/opt/homebrew/bin/brew update && \
/opt/homebrew/bin/brew install colima && \
colima start --cpu 4 --memory 8 --disk 60 && \
make go
```

Line by line:

1. **`sudo chown -R "$(whoami)" /opt/homebrew`** — On this specific Mac,
   the Apple Silicon Homebrew installation at `/opt/homebrew` was owned
   by a previous user ("olivia"). This transfers ownership to the
   current user so `brew install` works without permission errors.
   This is a one-time fix; if your Mac is set up cleanly, you can
   skip this step.

2. **`brew update`** — Refreshes Homebrew's package index. On a long-
   running Mac this can take several minutes the first time.

3. **`brew install colima`** — Installs Colima (~50 MB) and its
   dependencies (`lima`, `qemu`). Builds an Apple Silicon-native
   binary.

4. **`colima start --cpu 4 --memory 8 --disk 60`** — Starts the Linux
   VM with 4 CPU cores, 8 GB RAM, and a 60 GB disk. Tuned for our
   stack (6 containers including pgvector × 2 + Caddy + Next.js +
   watcher + Metabase). First start takes ~90 seconds; subsequent
   starts are ~10 seconds.

5. **`make go`** — Our existing one-command stack bring-up. Works
   identically to before.

For routine use after migration:

```bash
colima start   # at the start of a coding session
make go        # bring up the stack
# ... work ...
make docker-down   # stop the stack
colima stop    # at the end of a session, if you want to free resources
```

The `colima start` step can be hooked into shell startup
(`~/.zshrc`) for full transparency:

```bash
# Append to ~/.zshrc
if ! colima status &>/dev/null; then
  colima start &
fi
```

---

## What about Docker Desktop's uninstall?

Docker Desktop does not need to be uninstalled — Colima and Docker
Desktop can coexist on the same machine. They listen on different
sockets by default (Colima at `~/.colima/default/docker.sock`,
Docker Desktop at `~/.docker/run/docker.sock`). The `docker` CLI
switches between them via `docker context use`:

```bash
docker context ls           # list available contexts
docker context use colima   # switch to Colima
docker context use desktop-linux   # switch back to Docker Desktop
```

For users who want to fully migrate, Docker Desktop can be uninstalled
to recover the ~1.5 GB of application disk space and the VM image
(potentially 100+ GB). Uninstall steps:

```bash
# Quit Docker Desktop if running
osascript -e 'quit app "Docker Desktop"'

# Remove the application
rm -rf /Applications/Docker.app

# Remove all Docker Desktop data (this is destructive — your volumes go too)
rm -rf ~/Library/Containers/com.docker.docker
rm -rf ~/Library/Application\ Support/Docker\ Desktop
rm -rf ~/Library/Group\ Containers/group.com.docker
rm -rf ~/.docker
```

If you have important data in Docker Desktop volumes (databases,
state), back them up first with `docker compose down -v` or by
exporting individual volumes. For our project specifically, **the
SQLite database is bind-mounted from the host** (`./data/archive.db`),
so it's safe regardless. The Postgres volumes are reconstructable
from SQLite via `pnpm pg-backfill`.

---

# Part 2 — Dockyard: lightweight Docker manager UI

## The gap

The one real loss from moving to Colima is **visual container
management**. Docker Desktop's UI lets you:

- See all containers at a glance with status, ports, image, uptime
- Click to start, stop, restart, or remove a container
- View streaming container logs
- Open a shell inside a container
- List, pull, and remove images
- Inspect and clean up volumes and networks
- Watch resource usage (CPU, memory, network I/O) live

In Colima, all of that is available via `docker` CLI commands. But for
visual people, for non-developers on the team, and for getting a quick
overall picture, the GUI is genuinely valuable.

**Dockyard fills that gap.**

---

## What Dockyard is

A self-contained, local-first, zero-dependency web app for managing
Docker containers, images, volumes, and networks. Same purpose as the
Docker Desktop GUI. None of the bloat.

Same philosophy as **the Clinic** (this repo's sibling sub-app):

- Lives in its own folder (`dockyard/`) at the repo root
- Single Python 3 stdlib server — `python3 server.py` is the complete
  startup; no `pip install`, no `npm install`
- Pre-built single-file HTML UI with Tailwind CDN — works in any browser
  without a build step
- Optional Vite + React rebuild path for the UI
- Optional Node.js CLI and MCP server for AI agent control
- Eventually extracted to its own GitHub repo
  (`marvelousempire/dockyard`)

The Docker socket already exposes a complete REST API. Dockyard is
fundamentally a **friendly wrapper around that API** with a clean UI.

---

## Personas

### Marvin — Developer using Colima
Lost the Docker Desktop GUI when moving to Colima. Wants to see his
containers visually, peek at logs, kill stuck containers without
remembering exact CLI flags. Doesn't want a 1.5 GB Electron app
running 24/7 to do this. Opens `http://localhost:5437` when he needs
it; closes the tab when he doesn't.

### Olivia — Office manager / non-engineer
Runs a few self-hosted apps on a shared Mac mini. Doesn't know `docker
ps` from `docker compose`. Needs to be able to look at a webpage,
see if the apps are running, click "restart" if one is misbehaving,
and read logs if she's worried.

### Liam — DevOps engineer on a remote server
Connects to a remote Docker daemon over SSH. Wants to manage it from
his laptop browser without installing Docker Desktop on the server.
Configures Dockyard to talk to a remote Docker socket via tunnel;
gets the same UI experience as local.

### Claude — AI agent assisting development
Doesn't need a UI. Needs an MCP server that exposes container
operations as tools so it can `dockyard_restart_container`,
`dockyard_show_logs`, etc., during a debugging session.

---

## P0 functional requirements (V1 — must ship)

### Containers
| ID | Requirement |
|---|---|
| C-01 | List all containers (running + stopped). Show: name, image, status, ports, started timestamp, uptime. |
| C-02 | Filter containers by state (running, stopped, all), by image, by compose project. |
| C-03 | Start a stopped container. |
| C-04 | Stop a running container (with timeout configurable). |
| C-05 | Restart a container. |
| C-06 | Remove a stopped container (with confirmation). |
| C-07 | Stream container logs in real time (`docker logs -f` equivalent). Tail option (last N lines). |
| C-08 | Open a shell inside a running container — `/bin/sh` or `/bin/bash`, auto-detect. Browser terminal via xterm.js. |
| C-09 | Inspect container details — env vars, mounts, networks, healthcheck status. |
| C-10 | Live stats: CPU %, memory usage, network I/O — updated every 2 seconds. |

### Images
| ID | Requirement |
|---|---|
| I-01 | List all images with repo:tag, size, created date, in-use status. |
| I-02 | Pull a new image by name. Stream progress. |
| I-03 | Remove an unused image. Confirm before removal. |
| I-04 | Prune dangling images. |

### Volumes & Networks
| ID | Requirement |
|---|---|
| V-01 | List all volumes with name, driver, mountpoint, size (if cheap to compute). |
| V-02 | Inspect a volume — which containers use it. |
| V-03 | Remove unused volumes (with confirmation). |
| N-01 | List networks with name, driver, scope, attached containers. |
| N-02 | Inspect a network. |

### Compose project view
| ID | Requirement |
|---|---|
| CP-01 | Group containers by `com.docker.compose.project` label. |
| CP-02 | Show project-level actions: start all, stop all, restart all, view all logs. |

### System
| ID | Requirement |
|---|---|
| S-01 | Show daemon info — engine version, OS, architecture, disk usage. |
| S-02 | Show Dockyard build SHA + version (mirrors `/health` Build pill from Claude Archive). |
| S-03 | Light / dark / auto theme toggle (same pattern as the rest of the stack). |
| S-04 | Local-only auth by default — only accepts connections from 127.0.0.1 / RFC1918. |

---

## P1 functional requirements (V2 — ship when ready)

| ID | Requirement |
|---|---|
| P1-01 | Pause / unpause containers. |
| P1-02 | Rename containers. |
| P1-03 | Edit container env vars + apply via restart. |
| P1-04 | Adjust container resource limits (CPU shares, memory limit). |
| P1-05 | Browse a remote registry (Docker Hub, GHCR, self-hosted). |
| P1-06 | Multi-engine switcher — toggle between Colima, OrbStack, remote daemons. |
| P1-07 | Save and restore named container configurations. |
| P1-08 | Token-based auth mode for remote / non-local use. |
| P1-09 | MCP server: AI agents can call `dockyard_*` tools to operate the daemon. |
| P1-10 | CLI tool — `pnpm dockyard restart <name>` etc., for shell scripts. |

---

## Out of scope (V2+ — explicitly deferred)

- **Docker Swarm management** — out of scope, niche feature
- **Kubernetes management** — k9s/Lens already do this well
- **Image building** — use `docker build` in your terminal; building is
  a code activity, not a management activity
- **Extensions marketplace** — adds bloat we explicitly rejected
- **Sign-in / cloud sync** — local-first, no accounts
- **Telemetry** — no analytics, no phone-home
- **Auto-update mechanism** — `brew upgrade dockyard` is fine

---

## Architecture

Mirrors the Clinic exactly.

### Files

```
dockyard/
├── README.md
├── PRD.md                       (this document)
├── CHANGELOG.md
├── LICENSE                      (MIT)
├── server.py                    (Python 3 stdlib HTTP server)
├── web/
│   └── index.html               (pre-built single-file UI)
├── Makefile                     (make run / ui / doctor / certs)
├── dockyard.config.example.json
├── dockyard.config.schema.json
├── docker-compose.example.yml
├── src/                         (optional Node CLI + MCP)
│   ├── cli.ts
│   ├── mcp.ts
│   └── lib.ts
└── docs/
    ├── api.md                   (Dockyard HTTP API reference)
    ├── architecture.md
    └── mcp.md
```

### How the server works

`server.py` opens a connection to the Docker socket and acts as a
thin, security-aware HTTP wrapper. The Docker socket is a Unix domain
socket that speaks HTTP/1.1. Python's `http.client.HTTPConnection`
can talk to it directly via a custom socket override:

```python
import http.client, socket, json
from pathlib import Path

SOCKET_PATH = Path.home() / ".colima/default/docker.sock"

class DockerConn(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(str(SOCKET_PATH))

def list_containers():
    c = DockerConn("localhost")
    c.request("GET", "/containers/json?all=true")
    return json.loads(c.getresponse().read())
```

That's the whole architecture. Every Dockyard operation is a thin
shim around the Docker socket, with HTTP wrapping, schema validation,
auth checks, and JSON response shaping.

### Docker Engine API surface we wrap

The Docker daemon exposes a complete REST API at the socket. Dockyard
wraps the subset relevant for management:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/containers/json?all=true` | List containers |
| `GET` | `/containers/{id}/json` | Inspect |
| `POST` | `/containers/{id}/start` | Start |
| `POST` | `/containers/{id}/stop?t=10` | Stop with timeout |
| `POST` | `/containers/{id}/restart?t=10` | Restart |
| `DELETE` | `/containers/{id}?force=false` | Remove |
| `GET` | `/containers/{id}/logs?follow=1&stdout=1&stderr=1&tail=200` | Stream logs |
| `POST` | `/containers/{id}/exec` | Create exec session |
| `POST` | `/exec/{id}/start` | Start exec, hijack for stdio |
| `GET` | `/containers/{id}/stats?stream=1` | Live stats |
| `GET` | `/images/json?all=true` | List images |
| `POST` | `/images/create?fromImage=nginx&tag=latest` | Pull |
| `DELETE` | `/images/{id}?force=false` | Remove image |
| `GET` | `/volumes` | List volumes |
| `DELETE` | `/volumes/{name}` | Remove volume |
| `GET` | `/networks` | List networks |
| `GET` | `/info` | Daemon info |
| `GET` | `/version` | Daemon version |
| `GET` | `/events` | Live event stream |

Full reference: <https://docs.docker.com/engine/api/v1.45/>

### Web UI

Single-file `web/index.html` with Tailwind CDN. Sections:

```
┌──────────────────────────────────────────────────┐
│  ⚓ Dockyard     [Containers] [Images] [Volumes] │  ← top bar
│                  [Networks] [System]              │
├──────────────────────────────────────────────────┤
│                                                  │
│  [filter pills]   [search]   [+ Pull image]     │
│                                                  │
│  ┌────────────────────────────────────────────┐ │
│  │ ● claude-archive-app-1                     │ │
│  │   nginx:1.25  ·  :3000→3000  ·  up 2h 14m  │ │
│  │   [▶] [■] [↻] [logs] [shell] [✕]          │ │
│  └────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────┐ │
│  │ ○ claude-archive-db-1                      │ │
│  │   pgvector/pgvector:pg16  ·  :5433→5432   │ │
│  │   [▶] [■] [↻] [logs] [shell] [✕]          │ │
│  └────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

Live updates via SSE for stats and logs. No polling spam.

### Configuration — `dockyard.config.json`

```jsonc
{
  "$schema": "./dockyard.config.schema.json",
  "identity": {
    "name": "Dockyard",
    "tagline": "Docker, minus the bloat",
    "emoji": "⚓",
    "accent_color": "#0ea5e9"
  },
  "server": {
    "port": 5437,
    "ui_enabled": true,
    "tls": { "enabled": null, "cert": "./certs/cert.pem", "key": "./certs/key.pem" }
  },
  "docker": {
    "socket_path": "~/.colima/default/docker.sock"
  },
  "auth": {
    "mode": "local",
    "token_env": "DOCKYARD_TOKEN"
  }
}
```

### MCP server (P1)

Same shape as the Clinic's MCP integration. Tools:

```
dockyard_list_containers
dockyard_start_container(id|name)
dockyard_stop_container(id|name)
dockyard_restart_container(id|name)
dockyard_logs(id|name, tail=200)
dockyard_exec(id|name, command)
dockyard_list_images
dockyard_pull_image(name)
dockyard_stats(id|name)
```

Register with Claude Code:

```bash
claude mcp add --scope user dockyard -- \
  pnpm --silent --dir "$(pwd)/dockyard" mcp
```

Then any Claude session can `dockyard_restart_container("claude-archive-app-1")`
during a debugging session.

---

## Non-functional requirements

### Performance
- Container list renders 100+ containers in < 100ms
- Log stream latency < 500ms from `docker logs` output to browser
- Live stats refresh at 2 Hz without bogging the browser

### Footprint
- Total install: < 50 MB (vs Docker Desktop's ~1.5 GB)
- Runtime memory: < 100 MB idle (vs Docker Desktop's ~500 MB)
- Zero background processes when not in use — server only runs when
  you `make run`

### Privacy
- Default auth: local-only (127.0.0.1 + RFC1918)
- No telemetry, no phone-home, no analytics
- No external API calls except registry image pulls (which the daemon
  does, not Dockyard)
- HTTPS supported via the same Caddy pattern used elsewhere in this
  stack

### Compatibility
- Python 3.9+ (any platform)
- Docker Engine API 1.40+ (covers Colima, Docker Desktop, OrbStack,
  Podman 4+, dockerd direct)
- Browsers: Chrome, Firefox, Safari, Edge — modern only

---

## Success metrics

| Metric | Target |
|---|---|
| Time from "Docker Desktop is unable to start" to a working alternative | < 5 minutes (migration playbook) |
| Time to list 50 containers in Dockyard | < 100ms |
| Memory usage with Dockyard idle | < 100 MB |
| Total app install size | < 50 MB |
| Coverage of Docker Desktop's container management features | ≥ 80% by V1 |
| AI agent ability to manage containers via MCP | All 9 P0 tools available |

---

## Distribution

Same arc as the Clinic:

1. **V0 — Pre-build** (current). PRD written. Folder seeded.
2. **V0.1 — Server scaffold**. `server.py` listing containers,
   `web/index.html` showing them. No actions yet.
3. **V0.5 — Container actions**. Start, stop, restart, remove, logs.
4. **V1.0 — Full P0**. Exec terminal, images, volumes, networks, stats.
5. **V1.5 — MCP**. AI agents can drive Dockyard.
6. **V2.0 — Extract**. Move to its own GitHub repo
   (`marvelousempire/dockyard`). Mirror the
   `clinic/COPY-INTO-PROJECT.md` pattern.

---

## Change history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-05-13 | Initial PRD. Pre-build phase. Folder seeded with this document. |

---

# Closing note

This PRD covers two related decisions made together:

- **Why we moved to Colima** (Part 1) — a defensive change forced by
  Docker Desktop's failure modes
- **What we'll build to recover what we lost** (Part 2) — Dockyard, a
  proactive next step that fits our build philosophy

Both decisions reinforce the same principles that have shaped this
project: **local-first, low-overhead, drop-in compatible, no cloud
required, no lock-in, opt-in everywhere**.

Same as the Clinic. Same as the Blueprint. The pattern compounds.

---

## Platform support

Dockyard works on any host that exposes a Docker Engine API socket.
The socket-detection logic ([`dockyard/lib/socket.py`](./lib/socket.py))
probes in this order; the first reachable wins.

### macOS (Apple Silicon — primary target)

| Engine | Socket path | Notes |
|---|---|---|
| Colima default profile | `~/.colima/default/docker.sock` | Recommended (see Part 1) |
| Colima custom profile | `~/.colima/<profile>/docker.sock` | Auto-iterated |
| OrbStack | `~/.orbstack/run/docker.sock` | Drop-in alternative |
| Docker Desktop | `~/Library/Containers/com.docker.docker/Data/docker.raw.sock` | Still works if you have it |

### macOS (Intel)

Same as Apple Silicon — paths are user-relative. Performance on Intel
is slower because the Linux VM is emulated; that's a Docker limitation,
not a Dockyard one.

### Linux (native)

| Engine | Socket path | Notes |
|---|---|---|
| dockerd (native) | `/var/run/docker.sock` | Most distros, root-owned. Add your user to the `docker` group, or run Dockyard as root. |
| Rootless dockerd | `$XDG_RUNTIME_DIR/docker.sock` | Set `DOCKER_HOST=unix://$XDG_RUNTIME_DIR/docker.sock` and Dockyard picks it up via the env-var probe. |

### Windows (WSL2)

The recommended path is to run Dockyard **inside WSL2** (Ubuntu, Debian,
etc.) and talk to a Linux-native dockerd installed in the same WSL
distro (`sudo apt install docker.io`). The socket is `/var/run/docker.sock`.

For users with **Docker Desktop on Windows** (WSL2 backend), expose
the socket from WSL by setting `DOCKER_HOST` in WSL:

```bash
export DOCKER_HOST="unix:///mnt/wsl/shared-docker/docker.sock"
```

Native Windows (no WSL) is **not supported in V0** — Dockyard uses
`socket.AF_UNIX`, which requires WSL or Cygwin. V1 may add named-pipe
support (`//./pipe/docker_engine`).

### Remote daemons (deferred to V1)

`DOCKER_HOST=tcp://…` and `DOCKER_HOST=ssh://…` are read by the probe
but currently fall through. V1 adds TCP + SSH transport to the socket
adapter; the rest of the server stays unchanged.

### Override

If auto-detect picks the wrong engine (for example you run both Colima
and OrbStack), pin the path in `dockyard.config.json`:

```json
{ "socket": "/Users/you/.colima/team/docker.sock" }
```

`make doctor` will validate against that exact path.
