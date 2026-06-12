# Cassette self-announce — every backend writes its live port, serves under its name, never kills a port

## The verbatim source (stated by Avery 2026-06-12)

> why do you leave on the 127 ip instead of a real name like dustpan.localhost
> and a port you find available like the rest of the Cassettes? view cursor
> history and see how these Cassettes work and Player and the React Connecter
> plugging into components from anywhere anytime instant and fast. tell me what
> i mean and do it so we got this in SOP compliant.

Said after watching an agent open DustPan at a hardcoded `http://127.0.0.1:8765`
and **kill whatever held the port** — the exact anti-pattern of
[`cassette-discipline`](cassette-discipline.md) (RL-0066). A cassette is supposed
to find a free port, serve under its own name, and *announce* where it landed so
the Player and the React Connector find it — never squat a fixed IP+port.

## The rule

Every cassette/agent **backend** in the operator stack MUST, on bind:

1. **Auto-port, never squat.** Try a preferred port, then fall through to the
   next free one (or an OS-ephemeral port). **Never kill the process holding a
   port.** A second instance gets the next free port and re-announces — it does
   not evict the first.
2. **Announce its live address.** Write `~/.nephew/run/announce/<id>.json` =
   `{ id, host:"<id>.localhost", bind_host, backend_port, pid, started,
   direct_url, gateway_url, canonical_url }` **atomically** on bind, and remove
   it on exit (`atexit` / signal handler). Also write the cassette's own
   portfile (e.g. `~/.dustpan/run/dustpan.json`) so first-party tools read the
   real port instead of a hardcoded literal.
3. **Serve under its name, not an IP.** The canonical URL is `<id>.localhost` —
   the **Player gateway door** (`http://<id>.localhost:8782/`) when the family
   tape gateway is up, else the **direct name** (`http://<id>.localhost:<port>/`).
   `*.localhost` resolves to loopback with no `/etc/hosts` edit. Open and print
   the canonical URL; show the raw `127.0.0.1:<port>` only as a dim "Direct"
   fallback line.
4. **Expose the Speaker contract.** `GET /health` (liveness — the fact that it
   answers proves the cassette is up) and `GET /api/v1/health`, plus a deep
   `GET /doctor` probe. These are how the Player renders a true status LED
   (ties to [`os-pill-and-about-modal`](os-pill-and-about-modal.md) +
   [`live-dashboard-pattern`](live-dashboard-pattern.md)). `/health` must be
   reachable **without auth** in network mode so the gateway can probe it.
5. **Never hardcode the port anywhere else.** Every place that previously baked
   in `8765` (about payload backend string, known-services table, CLI
   `expose`/URL printers, remote-agent launchers, `/api/status`) reads the live
   `SERVER_PORT` / the announced portfile instead.

The **Player gateway** completes the contract: it prefers the announced
`backend_port` from `~/.nephew/run/announce/<id>.json` (pid-checked) over any
global backend port, so `<id>.localhost:8782` always reaches the *live* backend
even after it auto-ported off a busy default.

## When this fires

- Building or refactoring any cassette/agent **backend** (Python, Node, or
  otherwise) that binds a port and is meant to plug into the Player
- Reviewing a PR that opens a service at a hardcoded `127.0.0.1:<fixed-port>`
- Any time you catch yourself about to `lsof -ti :PORT | xargs kill` to free a
  port for your own service — STOP; auto-port + announce instead
- Adding a new `<id>.localhost` door to the family tape gateway

## When this does NOT fire

- Pure client code with no listening socket
- Third-party services we don't own (Portainer, n8n, GitLab) — they get a
  gateway door + a health probe, but we don't add self-announce to their code
- One-shot CLI commands that don't stay resident

## Reference implementation

DustPan is the reference:

- `dustpan/web/cassette.py` — `announce(bind_host, port)`, `cleanup()`,
  `canonical_url(port)`, `gateway_up()`. Pure stdlib, every write best-effort
  (no Player on the machine → still serves directly).
- `dustpan/web/server.py main()` — `find_open_port(PREFERRED_PORT)` →
  `cassette.announce(HOST, port)` → open `cassette.canonical_url(port)`;
  `/health` + `/api/v1/health` routes; stale-port refs fixed to `SERVER_PORT`.
- `nephew/scripts/family-tape-gateway.mjs` — `announcedBackendPort(id, fallback)`
  consulted in `proxyToTape`.

## Examples

### ✓ Compliant

Start DustPan with no `XCC_UI_PORT`: it picks a free port, writes
`~/.nephew/run/announce/dustpan.json` with the real port, and opens
`http://dustpan.localhost:8782/` (gateway up) or `http://dustpan.localhost:<port>/`
(gateway down). A second instance picks the *next* free port and re-announces —
the first keeps running. `curl http://dustpan.localhost:8782/api/status` returns
`server_port` == the live port because the gateway routed to the announced backend.

### ✗ Violation

```python
PORT = 8765
subprocess.run(["lsof", "-ti", f":{PORT}"])  # ... then kill it
webbrowser.open(f"http://127.0.0.1:{PORT}")   # squats a fixed IP+port, evicts the holder
```

No announce, no name, kills a neighbor. The Player can't find it; the next
service that wanted 8765 is gone.

## Propagation

Per [`rule-propagation-discipline`](rule-propagation-discipline.md): canonical
body in `nephew/.claude/rules/cassette-self-announce.md`, mirrored to
`.cursor/rules/` and every operator repo's `.claude/rules/` + `.cursor/rules/`.

## Related

- **Parent rule:** [`cassette-discipline`](cassette-discipline.md) — host=Player,
  plug-ins=cassettes; this rule is the *backend port + Speaker* half of it
- **Plan:** `dustpan/plans/0075-cassette-self-announce.md`
- **Speaker LED:** [`os-pill-and-about-modal`](os-pill-and-about-modal.md),
  [`live-dashboard-pattern`](live-dashboard-pattern.md)
- **Pain Journal:** `dustpan/CLAUDE.md` → `Serve-1`
- **Philosophy:** [`contracts-and-prudence`](contracts-and-prudence.md) — the
  announce file IS the contract; killing a port is the careless anti-contract
