# Dockyard — Plans

The audit trail of *why* Dockyard exists and *how* it grew. Every
substantive change to Dockyard starts as a numbered plan committed
here. Plans are git-tracked and immutable.

## Convention

- Filename: `NNNN-snake-case-title.md`
- Sections: **Context** (why), **Approach** (the one we picked),
  **Critical files** (paths created/modified), **Verification**
  (how we know it worked)
- Ship marker: `Status: shipped (commit <sha>)` at the top when done
- Append-only numbering. Don't edit old plans — supersede with new ones.

## Index

These four plans were originally numbered 0011–0014 in
[marvelousempire/claude-chat-reader/plans](https://github.com/marvelousempire/claude-chat-reader/tree/main/plans),
the repo where Dockyard was incubated. Copied here at extraction time
(Plan 0015 / 0016) so this standalone carries its full design history.
From here on, new Dockyard plans are written in this repo using the
standalone's own numbering.

| # | Title | Status | Original number in parent |
|---|---|---|---|
| [0001](0001-colima-decision.md) | Colima decision record + Dockyard PRD seed | shipped | 0011 |
| [0002](0002-v0-build.md) | Dockyard V0 build + plan-first workflow rule | shipped | 0012 |
| [0003](0003-v0.3-gaps-elevations.md) | v0.3 — close every gap + ship every elevation | shipped | 0013 |
| [0004](0004-one-keystroke-boot.md) | One-keystroke boot — heal DD hangs, install Colima, expose on Wi-Fi | shipped | 0014 |

## Why this folder exists

Plans get lost in chat. By writing them into the repo, we get:

- **Searchable history** — six months from now, "why did we move from
  Docker Desktop to Colima?" has an answer.
- **Continuity across Claude Code sessions** — a new session can read
  `plans/` and pick up where the last left off.
- **A defensible record** when something looks weird in the server,
  the UI, or the boot script — the plan that proposed it is right here.

## See also

- The original parent repo:
  [marvelousempire/claude-chat-reader](https://github.com/marvelousempire/claude-chat-reader)
- The sibling sub-app:
  [marvelousempire/clinic](https://github.com/marvelousempire/clinic)
- The pattern these plans all follow:
  [BLUEPRINT (in parent)](https://github.com/marvelousempire/claude-chat-reader/blob/main/BLUEPRINT.md)
