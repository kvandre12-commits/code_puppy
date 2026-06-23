# Agent Stack Governance

_Last updated: 2026-06-21_

Purpose: define the current agent stack that this checkout participates in,
what each layer is allowed to do, and which artifacts or controls are actually
authoritative.

This document exists so we stop hand-waving across Code Puppy, DroidPuppy,
Project OS, SharpEdge, and broker-side execution.

Machine-readable companion:
- `docs/agent_stack_inventory.json`

## One-sentence doctrine

```text
SharpEdge decides what should happen.
Code Puppy + DroidPuppy coordinate how bounded work happens.
Capabilities perform the work through explicit contracts and authority gates.
Android is one governed execution surface, not the whole architecture.
```

If a design blurs those roles, the design is wrong.

## Lineage note

The lineage helps explain the mental trap here:

- **SharpEdge** is the older identity/intention thread.
- **DroidPuppy** is the Android overlay/capability thread.
- **Project OS governance** is the orchestration/authority/recovery thread.

So when Android tooling starts feeling like the whole project, that is usually a
category error. Android is an important brick, but still only one brick of the
larger governance and operator stack.

## What this checkout owns

This repository is a Code Puppy working fork with a DroidPuppy Android overlay.
It owns runtime infrastructure, plugin surfaces, Android execution helpers,
contract plumbing, and execution containment.

It does not own SharpEdge signal truth, broker policy, broker credentials, or
live-order authority.

Read alongside:

1. `OWNERSHIP.md`
2. `docs/CROSS_REPO_WORK_LEDGER.md`
3. `docs/REPO_INVENTORY.md`
4. `DroidPuppy/docs/PROJECT_OS_BRIEF.md`
5. `DroidPuppy/docs/ORCHESTRA_AGENT.md`
6. `DroidPuppy/contracts/README.md`

## The current stack

| Layer | Role | Source path(s) in this checkout | Allowed to decide | Not allowed to decide |
| --- | --- | --- | --- | --- |
| SharpEdge intent layer | domain goal / market intent / operator goal | mostly external to this checkout; referenced by skills/docs | what should happen | exact Android action route, broker-side autonomous execution here |
| Code Puppy runtime | agent runtime, tool execution, plugin loading | `code_puppy/agents/`, `code_puppy/callbacks.py` | how agents are loaded, invoked, and instrumented | domain truth, broker permission |
| DroidPuppy overlay | Android-native orchestration + device capabilities | `DroidPuppy/`, Android plugins under `code_puppy/plugins/` | how Android-side work is performed | whether a domain action is justified or whether Android should become the architecture |
| Project OS supervisor | operator-facing service orchestration | `code_puppy/plugins/project_os_supervisor/` | how local services/manifests are started, observed, tailed | domain authority, broker permission |
| Authority gateway | execution containment and lease enforcement | `code_puppy/plugins/authority_gateway/` | whether a tracked effectful action is currently permitted | whether a business objective is good |
| Puppy Kennel | shared memory substrate | `code_puppy/plugins/puppy_kennel/` | what durable notes/history are stored and recalled | permission to act |
| Broker delegation seam | downstream broker-side handoff | `code_puppy/plugins/chatgpt_robinhood_delegate/` | how to package a broker request for an approved downstream operator flow | live autonomous broker authority |
| Capabilities | concrete tools and adapters | Android/browser/intent/CDP/UI/logcat/etc. plugins | how one bounded effect is executed | why the effect should exist |

## Governance model

### 1. Intent is upstream

SharpEdge or the operator may define the goal.

Examples:
- inspect an Android workflow
- collect a support bundle
- route a browser session
- prepare a broker handoff

This checkout may help execute, observe, validate, and package that work.
It does not get to invent domain truth just because it has a shell and a lot of
plugins.

### 2. Coordination is local

The local coordinator layer is Code Puppy plus DroidPuppy plus Project OS style
contracts.

This layer may:
- decompose work
- select tools/plugins
- produce operator-facing artifacts
- route through approval/authority gates
- recover from local failures
- preserve observable state

This layer may not silently convert intention into irreversible action.

### 3. Execution is capability-scoped

Concrete actions happen through capabilities:
- shell
- filesystem
- Android intents
- browser open/CDP
- UI dump/input
- app launch
- screenshots/logs/support bundles

Capabilities are intentionally dumb. They should be swappable and observable.
A capability is not a policy engine.

### 4. Authority is explicit

Permission is not inferred from convenience.

The current authority boundary in this checkout is the execution-containment
stack:
- explicit execution leases
- principal-bound scope
- optional narrowing by exact tool/path/browser/package/action
- anomaly-triggered breaker behavior
- short quarantine cooldown after containment events
- audit events validated against the shared DroidPuppy v2 audit contract

If a path bypasses these principles for high-effect work, it is governance debt.

## Canonical authority rules

### In this checkout

The following are authoritative for runtime permission in this repo:

1. execution lease state
2. authority gateway policy evaluation
3. breaker/quarantine containment state
4. contract-valid audit events for authority actions

The following are **not** authoritative permission objects:
- memory entries
- operator notes
- plans
- workflow summaries
- support bundles
- UI observations
- dashboard-style status output

### Imported SharpEdge doctrine

The broader SharpEdge operator stack defines four canonical agent-language
objects:

- `workflow_state` — what is true now
- `execution_plan` — what should happen next if conditions allow
- `approval_decision` — what is actually authorized
- `journal` — what happened and what was learned

Only `approval_decision` is authoritative permission in that doctrine.

This checkout now adds two governed companion artifacts around that core:

- `intent_handshake` — the raw operator request normalized into a durable,
  bounded handshake before the chain reasons too far ahead
- `workflow_commit` — a durable receipt freezing the current handshake, plan,
  and approval posture so a workflow can later graduate into a skill or tool

These two artifacts improve control flow, but they do not outrank
`approval_decision`. A commit receipt is not fresh permission.

That operator layer is mostly outside this checkout, but we adopt the rule here:
**status, plans, memory, handshakes, and commit receipts are not permission**.

## Repo-shipped governance agents

This checkout now ships project JSON agents mirroring that doctrine:

- `workflow-state`
- `execution-plan`
- `lease-request`
- `approval-decision`
- `workflow-commit`
- `lease-audit`
- `journal-audit`
- `governance-orchestrator`

`governance-orchestrator` exists to run the chain explicitly instead of letting one giant agent answer blur facts, plans, lease needs, authority, commit, and audit together.

These agents now bind to the DroidPuppy canonical context packet:
- `workflow-state` reads the packet and writes only `workflow_state`
- `execution-plan` reads the packet and writes only `execution_plan`
- `lease-request` reads the packet plus authority posture and writes the lease-shaped prerequisite back into `execution_plan`
- `approval-decision` reads the packet and writes only `approval_decision`
- `workflow-commit` reads the packet and writes only the governed commit receipt
- `lease-audit` reads the packet plus authority-gateway telemetry and appends/writes journal reconciliation about lease reality
- `journal-audit` reads the packet and appends/writes only journal state
- `governance-orchestrator` initializes/reads the packet, captures handshake intent, and tells the chain to use it

That keeps transcript context advisory while the typed packet becomes the durable workflow governor.

Operator shortcut:
- `/workflow-commit [optional request text]` is an orchestrated prompt wrapper, not a raw authority object and not the low-level commit tool itself. It forwards a structured prompt that tells a governance-capable agent to capture/refresh the handshake, reconcile the canonical packet, and create a governed workflow commit receipt when appropriate.
- `/wcommit [optional request text]` is the short alias. Example: `/wcommit to discord`

Portable repo setup:
- `droidpuppy_context_install_repo_governance(target_root="/path/to/repo")` scaffolds this same `.code_puppy/agents/` governance stack into another repo.
- That keeps the handoff steps boring and repeatable instead of making every repo reinvent the same haunted governance blob.
- After install, the target repo can use the same `/workflow-commit` / `/wcommit` entrypoint and the same authority rule: `approval_decision` is the only permission object.
- The portable stack now also includes dedicated lease shaping and lease auditing agents so every repo can ask for narrow authority and inspect live gateway reality with the same boring structure.

## Broker / Robinhood routing rule

Broker-adjacent work must be split into two different classes:

1. **Local bounded validation/configuration work**
   - examples: inspect MCP config, validate OAuth assumptions, check repo artifacts, assess whether a broker path is wired
   - these can be planned and, if appropriate, approved locally as bounded repo work

2. **Real broker-side account/order work**
   - examples: account reads through the actual broker surface, order drafts for submission, submit/cancel/replace actions
   - these are **not** to be represented as directly executable here unless a real authorized surface is in evidence
   - if the live authority is downstream, route via `approval-decision` into `chatgpt_robinhood_delegate` or another explicit broker surface
   - write-style requests remain operator-confirm-required

This rule prevents the classic nonsense where OAuth research, config notes, or MCP optimism get mistaken for actual live broker authority.

## Stack surfaces already present in this repo

### Runtime substrate

Source:
- `code_puppy/agents/`
- `code_puppy/callbacks.py`

Responsibilities:
- agent construction and invocation
- streaming / runtime plumbing
- plugin callback integration
- tool registration and advertisement

Governance rule:
- prefer plugins over core edits whenever a hook already exists

### Android operating layer

Source:
- `DroidPuppy/`
- Android-focused plugins under `code_puppy/plugins/`

Responsibilities:
- expose phone-native hands to the runtime
- keep Android interaction typed, documented, and testable
- route real observations/actions through bounded tools

Governance rule:
- DroidPuppy decides **how** to perform a device action, not **whether** the
  domain objective is valid

### Project OS supervisor

Source:
- `code_puppy/plugins/project_os_supervisor/`

Responsibilities:
- manifest-driven service orchestration
- operator snapshot generation
- operator brief and action hints
- service status + event tailing

Governance rule:
- operator snapshot / brief artifacts describe local system state; they do not
  grant permission for unrelated effectful work

### Authority gateway and containment

Source:
- `code_puppy/plugins/authority_gateway/`
- shared audit/lease schemas under `DroidPuppy/contracts/v2/`

Responsibilities:
- gate tracked effectful actions
- enforce principal and constraint scope
- revoke or quarantine after repeated suspicious behavior
- emit contract-valid audit events

Governance rule:
- tracked effects must be explainable in terms of lease scope, policy result,
  and audit trail

### Memory substrate

Source:
- `code_puppy/plugins/puppy_kennel/`

Responsibilities:
- durable repo/user/agent notes
- recall, recent history, wing listing, stats, inventory
- structured decision checkpoints for who/what/when/why capture
- cross-session continuity

Governance rule:
- memory is context, not authority
- write durable facts/decisions, not speculative noise
- capture hinge-point decisions when they become clear, not only at end-of-session

### Broker delegation seam

Source:
- `code_puppy/plugins/chatgpt_robinhood_delegate/`

Responsibilities:
- package downstream broker tasks for a separately configured ChatGPT connector
- keep write-style brokerage tasks operator-confirmed
- preserve constraints/risk notes in the handoff artifact

Governance rule:
- this repo may prepare or delegate broker work; it does not own live broker
  execution authority

## Cross-repo boundary rules

| Concern | Owning layer | Rule |
| --- | --- | --- |
| signal truth / market analytics | SharpEdge repo(s) / private prior art | do not recreate here unless explicitly promoting source from the real owner |
| Android execution mechanics | DroidPuppy / this checkout | okay to build here as infra |
| generic agent runtime / plugins | Code Puppy / this checkout | okay to build here as infra |
| broker-side permission and routing | SharpEdge bridge / downstream connector | document or delegate here; do not fabricate live authority |
| generated artifacts in `outputs/` | no permanent owner by default | treat as evidence until promoted into source |

## Required design rules

1. **Single authority object per decision seam.** Never let dashboards, memory,
   or plans impersonate permission.
2. **Contracts over vibes.** If a handoff matters, give it a schema or an
   explicit typed payload.
3. **Plugins before core sprawl.** Use `code_puppy/plugins/` and callback hooks
   whenever possible.
4. **Repo boundaries stay real.** Do not hide missing ownership by stuffing more
   domain logic into this checkout.
5. **Observability is mandatory.** High-effect flows need status, artifacts,
   audit events, or supportable logs.
6. **Containment beats optimism.** A capability that can do damage must be
   bounded by lease/policy/approval logic.
7. **Memory is for continuity, not justification.** Kennel notes can explain why
   something was done; they cannot authorize doing it again.

## Operator read order for future work

When touching governance or the agent stack in this checkout, read in this
order:

1. `OWNERSHIP.md`
2. `docs/AGENT_STACK_GOVERNANCE.md`
3. `docs/CROSS_REPO_WORK_LEDGER.md`
4. `docs/REPO_INVENTORY.md`
5. `DroidPuppy/docs/PROJECT_OS_BRIEF.md`
6. `DroidPuppy/docs/ORCHESTRA_AGENT.md`
7. `DroidPuppy/contracts/README.md`

## Near-term governance backlog

1. Add a lightweight machine-readable stack inventory artifact so the current
   layer map is inspectable without reading prose.
2. Make authority-gated tool surfaces easier to enumerate from the runtime.
3. Expand project-level operator artifacts so local status/plan/approval/history
   objects align more explicitly with the imported SharpEdge doctrine.
4. Keep the cross-repo ledger updated whenever governance logic is promoted,
   delegated, or moved across repos.

## Short takeaway

This checkout is not "the whole SharpEdge brain."

It is the runtime and Android-capability side of a broader stack.
Its job is to coordinate bounded work honestly, keep contracts and boundaries
clean, and never confuse memory or convenience with authority.
