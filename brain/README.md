# Dockyard — brain

Dedicated **Docker** memory stack for `dockyard`. Every Bishop-born agent gets its own brain — not shared with other agents.

## Quick start

```bash
cd agents/dockyard/brain
cp .env.example .env
docker compose up -d
docker compose ps
```

Default host port: **39584** (Postgres).

## Clinic / Dockyard

- Full provision template: `dockyard/brain-template` (Nephew Plan 0043)
- Clinic indexes minds loaded from this stack

## Boss

Reports to **bishop** per `manifest.json`.
