# Project OS Invariants

The Project OS has enough nouns. The next maturity step is laws.

This document defines structural invariants: relationships that must always be
true for the runtime to remain explainable and recoverable. These are not
scheduler policies, governance approvals, or operator preferences. They are the
kernel-level rules that keep Project OS state from turning into soup.

## Doctrine

```text
Evidence first. Behavior second.
Laws before policy.
Validation before automation.
```

Related doctrines:

```text
No direct power. Only granted power.
No scheduling without causality.
No causality without events.
No events without observability.
```

## Current primitive stack

```text
Project
  -> Objective
      -> Work Item
  -> Project Run
      -> Event Record
          -> Event Type
          -> Causality Trace
  -> Run Table
  -> Inspection
```

Implemented runtime primitives currently include Project Run state, Event
Records, Event Types, Causality Trace, Run Table, Inspection, and `why` views.
Some parent objects are still represented conceptually rather than as fully
normalized runtime tables. That distinction matters: constitutional invariants
can be defined before every backing table exists.

## Constitutional invariants

Constitutional invariants are intended to survive storage rewrites, scheduler
implementations, and agent-provider churn.

### 1. Every Project Run belongs to exactly one Project

A Project Run is not free-floating work. It is a resumable execution context for
a Project.

```text
Project -> Project Run
```

Implications:

- a Project Run cannot exist without a Project identity
- a Project Run must not switch Projects after creation
- agents attach to Project Runs; they do not own them
- provider/model/session changes must not change run identity

Current implementation note: the persisted run stores `project` as a string
rather than a normalized `project_id`. That is an implementation detail, not a
license for orphan runs.

### 2. Every Project Run has exactly one current objective

A Project Run exists to advance an objective-sized slice of work.

```text
Project -> Objective -> Project Run
```

Implications:

- a run cannot be created without an objective
- changing the objective should produce an `objective_changed` Event Record
- a future normalized Objective table should reject runs pointing at missing
  objectives

Current implementation note: the persisted run stores `objective` as a string.
That is acceptable for the first runtime primitive, but the invariant is that an
objective identity exists.

### 3. Every Work Item belongs to exactly one Objective

Work Items should not drift between objectives without an explicit change event.

```text
Objective -> Work Item
```

Implications:

- a Work Item cannot exist without an Objective
- completing a Work Item should produce `work_item_completed`
- moving a Work Item between Objectives should be modeled explicitly, not hidden
  in prose

### 4. Every Event Record belongs to exactly one Project Run

Events are evidence attached to a run.

```text
Project Run -> Event Record
```

Implications:

- `run_id` is required for every Event Record
- an Event Record cannot point at a missing Project Run
- an Event Record should not be reassigned to another run after creation
- Event Records are evidence, not scheduling behavior

Current implementation already validates run existence when recording events.

### 5. Every Event Record has exactly one Event Type

Event Types are the stable vocabulary for future scheduling policy.

```text
Event Record -> Event Type
```

Implications:

- `event_type` must be known to the catalog
- unknown event types must be rejected at write time
- free-form prose belongs in `payload_summary`, not `event_type`
- the scheduler must react to typed facts, not improvised strings

Current implementation validates Event Type names and normalizes hyphens to
underscores.

### 6. Event causality must point backward to an existing Event Record

A causal child may reference one parent Event Record.

```text
parent_event_id -> event_id
```

Implications:

- parent references must point at existing events
- causality traces must be acyclic
- root events have no parent
- a trace explains evidence, not policy

Current implementation validates parent existence and detects trace cycles.

### 7. Durable runtime state must not depend on an Agent, Model, or Provider

Agents are workers. Models and provider sessions are disposable.

```text
Project Run survives Agent Lease / Agent / Model / Provider session
```

Implications:

- a Project Run cannot require the original agent to resume
- event history cannot require a provider transcript to remain meaningful
- future Agent Leases must reference Project Runs, not replace them

### 8. Observability views must be read-only

Inspection commands answer questions; they must not change state.

Read-only views include:

```text
/project run list
/project run inspect <run_id>
/project run events <run_id>
/project run event-types
/project event trace <event_id>
/project run why <run_id>
```

Implications:

- read-only commands must not append events
- read-only commands must not mutate run status
- read-only commands must not infer missing scheduler, blocker, approval, wake,
  or lease state

## Cross-boundary references

Some references are allowed; others should be forbidden or heavily constrained.

### Allowed

```text
Project Run -> Project
Project Run -> Objective
Work Item -> Objective
Event Record -> Project Run
Event Record -> Event Type
Event Record -> parent Event Record
Agent Lease -> Project Run
Artifact -> Project / Objective / Work Item / Event Record
```

### Forbidden

```text
Agent -> owns Project
Agent -> owns Project Run
Model session -> owns Project Run
Event Record -> missing Project Run
Event Record -> unknown Event Type
Event Record -> missing parent Event Record
Work Item -> missing Objective
Agent Lease -> missing Project Run
Scheduler decision -> no triggering Event Record or causal explanation
```

### Constrained

Cross-run causality is possible but must remain explicit.

Example:

```text
Run A: artifact_created
  -> Run B: run_unblocked
```

This is allowed only if the child event stores the parent `event_id`. The system
must never imply cross-run causality from timestamps alone. Timestamps are not
causes. Cute try, entropy.

## Creation-time validation targets

These are the invariants that should eventually be enforced directly by runtime
write paths.

| Object | Required validation |
|---|---|
| Project Run | non-empty Project identity, non-empty Objective identity, unique `run_id` |
| Work Item | existing Objective identity |
| Event Record | existing Project Run, known Event Type, existing parent if supplied |
| Event Type | cataloged before use |
| Causality Trace | no cycles, no missing parent links |
| Agent Lease | existing Project Run, explicit granted scopes, expiry |
| Scheduler Decision | triggering Event Record or causal trace reference |

## Testable invariants

Tests should enforce invariants before features depend on them.

Current tests already cover:

```text
Project Run survives without agent/model fields
Event Record uses a known Event Type
Event Record cannot use an unknown Event Type
Event Record must point at an existing parent event if parent_event_id is set
Causality trace walks root -> selected event
Read-only views do not mutate persisted state
```

Next tests to add when backing objects exist:

```text
Project Run cannot point at a missing Project
Project Run cannot point at a missing Objective
Work Item cannot point at a missing Objective
Agent Lease cannot point at a missing Project Run
Scheduler decision cannot exist without a triggering Event Record
```

## Constitutional vs implementation detail

Constitutional:

```text
Every Project Run belongs to exactly one Project.
Every Project Run has exactly one current Objective.
Every Work Item belongs to exactly one Objective.
Every Event Record belongs to exactly one Project Run.
Every Event Record has exactly one Event Type.
Causality points to existing events and stays acyclic.
Agents lease runs; they do not own them.
Read-only observability commands do not mutate state.
```

Implementation detail:

```text
JSON vs SQLite vs another store
string project/objective fields vs normalized IDs
exact event_id formatting
exact table formatting in slash commands
whether journal remains separate from Event Records
how scheduler priority is scored
which provider/model executes a lease
```

Do not confuse storage shape with law. Laws should survive storage migrations.

## Non-goals

This document does not implement:

```text
Event Queue
Scheduler
Wake Policy
Agent Lease Allocation
Objective table
Work Item table
Project table
```

It defines the structural rules those future features must obey.
