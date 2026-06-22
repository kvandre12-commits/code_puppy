---
name: kennel-capture-discipline
description: How to preserve the who/what/when/why in Puppy Kennel without losing the best middle-of-session insights.
---

# Kennel Capture Discipline

Use this when a session is producing real decisions and you do **not** want the
best reasoning to disappear into transcript soup.

## The problem

The strongest insight often happens in the middle:
- a root cause becomes clear
- a boundary decision is made
- a weird failure mode is explained
- a policy/governance seam is clarified

If you only save memory at the very end, future-you sees the first few prompts,
the final summary, and misses the real hinge point.

## Rule of thumb

Capture memory when one of these becomes true:
1. **We chose X over Y**
2. **We learned why something failed**
3. **We established a boundary/authority rule**
4. **We built a reusable mechanism**
5. **We proved something with evidence**

## Preferred storage shapes

### Use `kennel_capture_decision(...)` for:
- architectural decisions
- governance/authority clarifications
- debugging root-cause findings
- test/proof outcomes worth reusing

Populate:
- `what`
- `why`
- `evidence`
- `outcome`
- `follow_up`
- `who` / `when` when helpful

Default room:
- `room="decisions"`

### Use `kennel_remember(...)` for:
- small factual notes
- conventions/gotchas
- short user preferences

Default rooms:
- `notes`
- `preferences`

## Wing discipline

- `wing="repo"` — default for most solved-problem memory
- `wing="user"` — only true cross-project user preferences
- `wing="agent"` — rare, only genuine cross-project agent lessons

## Good capture examples

### Debugging hinge point
- What: optional native imports are intentionally soft-failing on Android
- Why: runtime must degrade gracefully in sterile Termux installs
- Evidence: fresh upstream clone + no optional deps + import smoke passed
- Outcome: PR proof is stronger and docs were updated

### Governance rule
- What: approval_decision is the sole permission object
- Why: plans/memory/status must never masquerade as authorization
- Evidence: agent prompts + docs + packet tests updated
- Outcome: future agents have one authority seam instead of several fake ones

## Anti-patterns

Do **not** store:
- vague hype
- speculative guesses without evidence
- raw duplicate transcript blobs when a structured checkpoint would do
- permission claims in memory notes

## Core idea

The kennel should hold **retrievable seams**, not just diary residue.
When the middle matters, capture the middle.
