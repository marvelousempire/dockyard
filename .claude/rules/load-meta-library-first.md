---
name: load-meta-library-first
description: At the start of every Claude Code session in the dockyard repo, call nephew_session_load (from the nephew MCP, wired in .mcp.json) before any code reading, planning, or editing. The nephew MCP serves Historia + meta-library — the curated record of every prior session, decision, lesson, and incident across the control tower, including this project.
type: session-start
---

# Load the meta-library first — every session, no exceptions

## The contract

Before reading the codebase, opening files, planning, or replying with anything substantive in a fresh Dockyard session:

```text
nephew_session_load(query="<topic of this session>")
```

Where `<topic of this session>` is a 3–8 word summary of what the user just asked, e.g. `"disk monitoring elevations"`, `"control tower wiring"`, `"plan 0005 follow-ups"`.

If `nephew_session_load` is unavailable (MCP not connected, network down, nephew daemon dead), read these in fallback order, then proceed:

1. `~/Developer/nephew/docs/meta-library/INDEX.md`
2. `~/Developer/nephew/docs/meta-library/RETRIEVAL.md` — the shelf-routing table
3. The most recent `~/Developer/nephew/docs/meta-library/YYYY-MM-DD-session-learning.md`
4. `~/Developer/historia/catalog/claude/projects/project--Users-nivram-Developer-dockyard.json` — last-seen Dockyard session metadata

Announce out loud which path you took (MCP call or fallback file reads).

## Why this rule exists

The operator has already built the storage + sync side:

- **Historia** catalogs every Claude transcript at `~/.claude/projects/-Users-nivram-Developer-dockyard/*.jsonl` and ships them to a VPS via the `com.marvelousempire.historia-sync` LaunchAgent.
- **Meta-library** (`nephew/docs/meta-library/`) is the curated layer: daily session-learning digests, decisions, doctrine, incidents, lessons, operations, dependencies.
- **`nephew_session_load`** is the MCP that pulls the right slices into context at session start.

Without this rule, every new session in `dockyard` starts cold — the agent has no idea what was decided last week, what's been tried, or what just shipped. That contradicts the contracts-and-prudence philosophy (you cannot keep a contract you don't know exists) and wastes the operator's already-built memory infrastructure.

## How to apply

- **First message of every session in this repo:** call `nephew_session_load` before any other tool.
- **When the user asks about prior work** (`"what did we ship last?"`, `"where were we?"`, `"why did we choose X?"`): start with `nephew_session_load` (or grep meta-library) — do not rely on the live transcript alone.
- **When picking up a plan from `plans/`:** check meta-library for any session-learning entries about that plan number.
- **When you finish a substantive piece of work:** if it generated a new decision or doctrine, the day's `session-learning.md` should reflect it. (You don't write that file yourself — the operator's pipeline curates it. Just make sure your work is committed and pushed so the curator can see it.)

## What this rule is NOT

- Not a license to dump meta-library contents into the chat. Pull a tight slice.
- Not a substitute for reading the current code. Meta-library tells you *why* and *what was decided*; the repo tells you *what is true now*.
- Not optional based on session length or "how big" the task is. A typo fix still benefits from knowing the project's typography conventions are stored as a decision.

## Pinnable one-liner

> **Meta-library first. Code second. No exceptions in this repo.**
