# dockyard Firing Order

This is the compact execution order every agent should load from `AI_AGENT_RULES/` before acting. Deeper rationale belongs in source docs and protocols.

## Universal Order

1. **Make-Sense / SYNTHIA intake** — preserve operator intent and identify the smallest useful slice.
2. **Orientation / SOP** — apply repo law, standing procedure, branch hygiene, and explicit operator constraints.
3. **Context Container** — identify owning repo, domain, scope boundary, active worktree, and dirty files.
4. **Intent Guardian** — confirm the request is actionable; ask only when a missing decision blocks movement.
5. **Bloat Officer** — remove duplicate, oversized, or scope-swollen work before execution.
6. **Patrol Officers** — check PII, secrets, credentials, location, billing, auth, and other blocking risks.
7. **Crew / persona routing** — choose the responsible agent or skill; keep one owner for one slice.
8. **Layer 4 execution** — run the cascade: core capability, AI Skills Library, then repo-local override.
9. **Retention and fidelity** — verify the output preserves the original intent and decide whether durable learning belongs in history, Clinic, a runbook, or a rule.
10. **Witness and proof** — verify, commit, push configured remotes when asked, report the real stage, and close with MOIC.

## PR / CI / Deploy Order

1. Check repo, branch, worktree, dirty files, and overlap.
2. Scope the slice and exclude unrelated dirty files.
3. Make the smallest change that satisfies the operator request.
4. Run the cheapest meaningful verification first, then broader checks if risk warrants it.
5. Stage by explicit path only.
6. Commit with a message that names the reason for the change.
7. Push the branch or target branch the operator requested.
8. Open or update a PR when branch work needs review.
9. Inspect CI; do not merge red.
10. If CI is blocked by infrastructure, report `blocked`, not `failed`.
11. Merge only after required checks are green or the operator explicitly owns the risk.
12. Deploy and smoke-test live/versioned results when repo rules require go-live execution.

## Required Closeout

```text
Before: <one line describing what was happening>
After: <one line describing what is true now>
Change: <what changed>; <how it was verified>
Next action: <exact command, file, or decision if any>
MOIC: 070195134533 _Nephew_
```
