-- {{agent_name}} brain — minimal schema (extend per agent)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS agent_memory (
  id BIGSERIAL PRIMARY KEY,
  agent_name TEXT NOT NULL DEFAULT '{{agent_name}}',
  kind TEXT NOT NULL DEFAULT 'observation',
  content TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS agent_memory_agent_idx ON agent_memory (agent_name);
