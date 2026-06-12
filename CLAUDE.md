# Dockyard Claude Rules

Shared assistant policy lives in the operator's global rules and the
`.claude/rules/` catalog in this repo.

## Pain Journal — recurring failure modes & how to spot them

This is the repo's "medical history." Read it before debugging a recurring
mystery. Catalog *patterns* that took >15 min to diagnose and could bite again.
Entry format: Symptom · Diagnose (<30s) · Fix · Root cause · First seen ·
Prevention.

### Entries

#### 🔌 Serve-1 (seed): adopt cassette self-announce when this backend binds a port

- **Symptom (future):** the Player / React Connector can't find this service
  after it moves off its default port, or a port gets killed to free it.
- **Fix:** on bind, auto-port, write `~/.nephew/run/announce/<id>.json`, and
  serve under `<id>.localhost` — never a hardcoded `127.0.0.1:<fixed-port>`,
  never kill a port. DustPan's `web/cassette.py` is the reference.
- **Prevention:** [`.claude/rules/cassette-self-announce.md`](.claude/rules/cassette-self-announce.md).
  Wiring this service's announce is a Phase 2 task of plan 0075.
