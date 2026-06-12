---
name: name-the-surface-before-version
id: RL-NSBV
keywords: [version, surface, ambiguity, control-tower, family-hub, naming, receipt]
goal: Every version number is preceded by the name of the surface it versions — never a bare "v1.72.2".
relations: [moic-response-signatures, human-readable-timestamps, pipeline-stage-truth]
governed_by: [global]
meta: dynamic
---

# Name the surface before the version — never a bare version number

## The verbatim source (stated by Avery 2026-06-12)

> when you were saying this … "hip, changelog, GitHub release, and /api/v1/version
> all read v1.72.2" … I never knew you were talking about the CT. I thought you were
> talking about the Hub v1. something — next time remember rules always say what
> before you say the version.

## The rule

When stating **any** version number to the operator, **name what it versions first**
— the app / component / surface — then the number. A bare version number is
forbidden.

The operator runs many **independently-versioned** surfaces — Nephew Control Tower,
Family Hub, DustPan, Clinic, Historia, ReadyPlay (marketing / admin / player-web),
the bank reader, Automata, Scene Skout, and more. "v1.72.2" with no noun is
ambiguous and will be read as the wrong thing (here: a Control Tower version was read
as the Family Hub).

- ✅ "Control Tower **v1.72.2**", "Family Hub **v1.4**", "the bank reader **v0.3**",
  "DustPan **v0.39.0**"
- ❌ "v1.72.2", "shipped 1.72.2", "the badge reads v1.72.2", "released 1.72.2"

## The bright line

If you are about to type `v` immediately followed by digits (or "version" + digits,
or "shipped/released/deployed" + digits), a **noun naming the surface** must come
immediately before it. If it doesn't, stop and add it.

## When this fires

Every version mention to the operator, on every surface:
- Chat replies, explanations, status updates
- MOIC closeout / receipt blocks (the `Before/After/Change/Next action` summary)
- Deploy confirmations ("X is live"), pipeline-stage reports
- CHANGELOG / GitHub release references, PR descriptions
- Tables or lists of releases — each row names its surface (a column header counts)

## When this does NOT fire

- Inside a code block, a `package.json`, a tag name, or a URL where the surface is
  already unambiguous from the immediate context (e.g. a `git tag v1.72.2` command
  whose surrounding sentence already named the surface).
- A continuous list under an explicit heading that already names the surface
  ("Control Tower releases:" followed by bare version rows) — the heading is the noun.

## Examples

### ✓ Compliant

> Deployed **Control Tower v1.72.2** — the version chip, the changelog, the GitHub
> release, and `/api/v1/version` all read 1.72.2.

### ✗ Violation (the incident this rule comes from)

> the chip, changelog, GitHub release, and /api/v1/version all read **v1.72.2** —
> verified live.

(No noun — the operator can't tell it's the Control Tower and not the Family Hub.)

## Why

Version numbers are identifiers, not just values. Across a multi-surface stack the
number alone doesn't identify the thing — the surface name does. Naming it costs one
word and removes a whole class of "wait, which app?" confusion.

## Propagation

Per [`rule-propagation-discipline`](rule-propagation-discipline.md): canonical body
here (`nephew/.claude/rules/name-the-surface-before-version.md`), mirrored to
`.cursor/rules/name-the-surface-before-version.mdc`,
`.nephew/rules/name-the-surface-before-version.md`, the global
`~/.claude/CLAUDE.md`, and operator memory
(`feedback-name-surface-before-version`). Applies to every operator repo and the
AI Skills Library as a cross-cutting communication rule.

## Related

- [`moic-response-signatures`](moic-response-signatures.md) — the closeout/receipt where bare versions most often slip in
- [`pipeline-stage-truth`](pipeline-stage-truth.md) — name the *stage*; this rule says also name the *surface*
- [`human-readable-timestamps`](human-readable-timestamps.md) — sibling "say it the way a human reads it" rule
- [`rule-propagation-discipline`](rule-propagation-discipline.md) — how this lands everywhere
