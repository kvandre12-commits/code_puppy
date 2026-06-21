# Cross-Repo Work Ledger

_Last updated: 2026-06-21_

Purpose: stop rebuilding the same systems in the wrong repo.

This ledger is the quick routing map for work that spans Code Puppy, DroidPuppy,
SharpEdge, private repos, and generated artifacts.

## Lineage and corrective framing

The rough lineage matters because it explains why the stack can feel muddled if
we do not write it down explicitly:

1. **SharpEdge** is the identity/name thread and the oldest conceptual root.
   The name comes from the first code the user wrote on GitHub, so it is not
   just branding slapped on later.
2. **DroidPuppy** is the Android agent overlay/capability line: phone-native
   tools, device observability, browser/CDP, UI automation, support bundles,
   and Android workflow experiments.
3. **Project OS / governance** is the higher-order control problem: contracts,
   authority, review boundaries, service orchestration, worker survivability,
   journals, and recovery semantics.

Corrective architecture sentence:

```text
Android is one brick of governance, not the whole building.
```

More concretely:

```text
SharpEdge = intent / identity / operator-facing direction
Code Puppy = runtime and plugin substrate
DroidPuppy = Android actuator and observation layer
Project OS governance = authority, orchestration, review, journals, recovery
```

If work starts collapsing those layers into one blob, stop and route it through
this ledger before writing more code.

## Default stance

The working demo already proves this stack can do real work:

```text
Code Puppy + DroidPuppy + Android security boundaries + Project OS doctrine
```

Do not re-litigate whether we can build these capabilities ourselves every
session. Assume the answer is yes where feasible. The real questions are:

```text
Which repo owns it?
What prior private/source-trail work already exists?
What should be promoted, reused, cleaned, or deliberately left alone?
What tests prove the integration still works?
```

## Rules

1. Read `OWNERSHIP.md` before implementing.
2. If a feature feels familiar, check this ledger before rebuilding it.
3. Private-repo prior art should be reused or promoted deliberately, not recreated.
4. Generated files in `outputs/` are evidence/prototypes, not stable source.
5. Promote prototypes into source only when the owning repo/layer is clear.
6. Do not ask if the premise is possible when a working demo/source trail already
   proves it; ask what the next integration/cleanup step is.

## Current repo: Code Puppy + DroidPuppy checkout

Owns:

- Code Puppy agent runtime and plugin framework.
- DroidPuppy Android tooling: ADB, UI dump/input, browser handoff, CDP helpers,
  app inventory, support bundles, workflow/orchestration experiments.
- Contract-driven Android execution experiments.

Does not own:

- SharpEdge trading truth or signal generation.
- Broker policy and live-order authority.
- Native SharpEdge app/UI product direction.
- Private-repo-only implementations unless explicitly promoted here.

## Active now / park for later

### Active now

- Cross-repo ownership clarity so we stop rebuilding the same systems.
- Governance-first architecture: authority objects, review boundaries,
  containment, and durable journals.
- Android worker survivability: checkpointing, recovery, bounded background
  execution, and operator-facing reconciliation.
- Promoting real prototypes into the right source repo instead of letting them
  rot in generated artifacts or memory.

### Park for later

- Rebuilding SharpEdge analytics/truth inside this checkout.
- Treating browser automation or Android UI automation as the architecture.
- Expanding Android polish/features before the governance and recovery seams are
  boringly reliable.
- Inventing a native product shell boundary before ownership with SharpEdge is
  explicit.

## Known high-value work outside this checkout

| Area | Likely owner | Notes |
| --- | --- | --- |
| SharpEdge trading/cockpit/analytics | SharpEdge repo(s) / private repo | Do not rebuild analytics or signal truth here. This repo may only integrate with it. |
| Best private-repo work | Private repo | Treat as prior art. Ask/check before recreating similar systems. |
| Broker execution governance | SharpEdge / bridge layer | This repo may delegate or document, not invent live-order authority. |
| Native Android assistant UX | TBD SharpEdge Android / DroidPuppy boundary | DroidPuppy can prototype Android actions; product UI ownership must be explicit. |

## Recent milestone chain

### Security / authority boundary milestones

| Date | Repo | Commit | Milestone |
| --- | --- | --- | --- |
| 2026-06-20 | Code Puppy | `c52e0ff` | Added deterministic execution lease gateway with lease store + audit trail hooks. |
| 2026-06-20 | DroidPuppy | `828e306` | Minted capability-scoped execution leases from the eyes review gate. |
| 2026-06-20 | Code Puppy | `55c3cbf` | Enforced runtime lease constraints: tool lock, path lock, browser lock, intent/package lock. |
| 2026-06-20 | DroidPuppy | `4cb1a7f` | Extended review-gate minting/CLI to preserve constrained lease payloads. |
| 2026-06-20 | Code Puppy | `4663aa0` | Added anomaly-triggered auto-revoke circuit breaker for repeated constraint hits and runaway shell/intent loops. |
| 2026-06-20 | DroidPuppy | `a45b723` | Updated v2 audit contract to allow `anomaly_detected` events. |
| 2026-06-20 | Code Puppy | `73bd737` | Added principal quarantine cooldown after breaker trips so post-revoke hammering is blocked before lease evaluation. |
| 2026-06-20 | DroidPuppy | `4d95f41` | Restored valid JSON for the v2 audit schema so root-side authority audit validation/writes work again. |

What this means in practice:

- Android effects now run behind explicit, principal-bound, capability-scoped leases.
- Leases can be further narrowed to exact tools, paths, browsers, intent actions, and target packages.
- Suspicious repeated violations or runaway low-level loops can zero out active lease authority automatically.
- After the breaker trips, the affected principal enters a short quarantine cooldown window; tracked tool calls are blocked before lease lookup so the system remembers that it just contained something sketchy.
- The containment stack depends on a valid shared audit contract: the root authority gateway validates against `DroidPuppy/contracts/v2/eyes_audit_event.schema.json`, so schema correctness is operational, not cosmetic.
- Full-repo Ruff sweep was brought back to green after the gateway/anomaly work, so the milestone is not just architectural poetry — it is validated source state.

## Governance / stack mapping milestones

| Date | Repo | Source | Milestone |
| --- | --- | --- | --- |
| 2026-06-20 | Code Puppy | `docs/AGENT_STACK_GOVERNANCE.md` + `docs/agent_stack_inventory.json` | Promoted a repo-local governance doctrine and machine-readable stack map covering layers, authority rules, repo boundaries, and imported SharpEdge operator semantics. |

## Current promoted prototypes

### Android media router

Source:

```text
code_puppy/plugins/android_media_router/
```

Promoted from earlier `outputs/` voice/music demos.

Canonical behavior:

```text
Hey SharpEdge play my favorite song
=> YouTube URL search
=> Jack Harlow Tyler Herro remix
```

```text
Hey SharpEdge play my fight song
=> Spotify exact track URI
=> Eye of the Tiger - Survivor
=> no generic media-play resume
```

Status:

- Plugin source now lives in-repo under `code_puppy/plugins/android_media_router/`.
- Keep it lean; do not expand into a broad media framework until voice reliability
  is proven.

## Before starting similar work

Ask:

1. Which repo owns the source of truth?
2. Did we already build this in a private repo or generated prototype?
3. Is this integration glue, product code, research, or runtime artifact?
4. What is the smallest promotion path from prototype to stable source?
5. What tests prove we did not just rebuild lasagna?

## Parking lot

Use this section to record things we suspect exist elsewhere but have not mapped yet.

- Private repo: best SharpEdge / assistant work exists there; map exact paths when accessible.
- Discord/community profile setup: operational/social identity, not code ownership.
