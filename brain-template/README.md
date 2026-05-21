# {{display_name}} — brain (Dockyard template)

Dedicated **Docker** memory stack for `{{agent_name}}`. Postgres 16 + pgvector — private to this agent.

## Quick start

```bash
cd brain
cp .env.example .env
docker compose up -d
docker compose ps
```

Default host port: **{{brain_port}}** (Postgres).

## Health

```bash
docker compose exec db pg_isready -U {{agent_name}} -d {{agent_name}}_brain
# or from Nephew repo root:
make -C ~/Developer/nephew brain-status BRAIN={{agent_name}}
```

## Boss

Reports to **bishop** per workspace catalog. Provisioned from `dockyard/brain-template` (Plan 0043).
