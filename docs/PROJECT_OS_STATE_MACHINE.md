# Project OS State Machine

Project OS has objects, identity, authority, events, and causality. The missing
law is lifecycle.

A Project Run must not move between states by vibes. Its lifecycle should be a
legal transition graph.

```text
Identity authorizes.
Authority permits.
Event triggers.
Causality explains.
State Machine constrains.
```

This document defines the Project Run state-machine doctrine. The first
read-only validator is exposed as `/project validate`. This doctrine still does
not implement scheduler behavior, mutating transition enforcement, wake policy,
approval queues, or lease allocation.

## Doctrine

```text
No event may create an illegal state transition.
No scheduler action may bypass state transition rules.
Every state transition is caused by an Event Record.
Every state transition is attributable to an Identity.
Every state transition requires Authority.
Every state transition preserves Causality.
```

Related doctrines:

```text
No authority without identity.
No action without attribution.
No state change without authority.
No scheduling without causality.
No causality without events.
Evidence first. Behavior second.
```

## Why this exists

Without a state machine, Project OS can eventually say nonsense like:

```text
completed -> running
archived -> resumed
blocked -> completed without unblock
waiting_approval -> running without approval
```

Those are lifecycle bugs, not merely ugly status labels. Operating systems become
reliable when object lifecycles are constrained.

## Current implementation note

The current Project Run store recognizes these status labels:

```text
created
ready
running
sleeping
waiting_event
waiting_approval
blocked
suspended
completed
failed
archived
```

Today they are accepted statuses, not a fully enforced transition graph. This
document defines the law future write paths must enforce.

## Project Run states

### created

The run record exists, but has not yet been admitted as schedulable work.

Meaning:

```text
Project Run identity exists.
Project and Objective are bound.
Initial Event Record should exist.
```

Typical entry event:

```text
run_created
```

### ready

The run is eligible to execute when an authorized scheduler/operator allocates
attention.

Meaning:

```text
not blocked
not waiting on approval
not already running
has enough context to resume
```

### running

The run currently has execution attention.

Meaning:

```text
an operator or leased agent is actively working the run
state changes may occur
checkpoint should be maintained
```

### sleeping

The run is paused safely and can be resumed later.

Meaning:

```text
no active execution attention
checkpoint is expected to be enough for continuation
not blocked by an external dependency
```

### waiting_event

The run is paused until a specific external or internal event occurs.

Meaning:

```text
waiting for evidence, time, device state, file, market open, webhook, etc.
```

### waiting_approval

The run is paused until an authorized identity grants or rejects approval.

Meaning:

```text
approval_requested exists
privileged action must not proceed
approval identity must be accountable
```

### blocked

The run cannot proceed because a blocker exists.

Meaning:

```text
missing dependency
failed prerequisite
operator input needed
external system unavailable
```

A blocked run may or may not require approval. Do not collapse blocker and
approval semantics unless evidence says they are the same thing. Lazy state
modeling is how systems grow mold.

### suspended

The run was intentionally paused by authority, policy, or operator focus.

Meaning:

```text
do not wake automatically unless a lawful resume event occurs
```

### completed

The run objective is done.

Meaning:

```text
normal execution lifecycle ended
future work should create a new run or explicit reopen event
```

### failed

The run ended unsuccessfully.

Meaning:

```text
execution cannot continue without explicit recovery/retry decision
```

### archived

The run is retained for history and should not execute.

Meaning:

```text
read-only historical record
not schedulable
not resumable without explicit restoration flow
```

## Legal transition graph

Baseline legal transitions:

```text
created -> ready
created -> sleeping
created -> blocked
created -> waiting_approval
created -> archived

ready -> running
ready -> sleeping
ready -> blocked
ready -> waiting_event
ready -> waiting_approval
ready -> archived

running -> sleeping
running -> blocked
running -> waiting_event
running -> waiting_approval
running -> completed
running -> failed
running -> suspended

sleeping -> ready
sleeping -> running
sleeping -> blocked
sleeping -> waiting_event
sleeping -> waiting_approval
sleeping -> archived

waiting_event -> ready
waiting_event -> running
waiting_event -> blocked
waiting_event -> waiting_approval
waiting_event -> archived

waiting_approval -> ready
waiting_approval -> running
waiting_approval -> blocked
waiting_approval -> archived

blocked -> ready
blocked -> waiting_approval
blocked -> suspended
blocked -> failed
blocked -> archived

suspended -> ready
suspended -> sleeping
suspended -> archived

failed -> ready
failed -> archived

completed -> archived

archived -> no automatic transitions
```

## Terminal and quasi-terminal states

Terminal by default:

```text
completed
archived
```

Quasi-terminal:

```text
failed
```

A failed run may be retried through explicit authority and evidence. A completed
run should not resume directly. If more work exists, create a new run or define a
future `run_reopened` event with explicit authority and causality.

No zombie Project Runs. Linux already has zombies; we do not need artisanal
markdown zombies too.

## Illegal transitions

These must be rejected unless a future doctrine explicitly defines a recovery
flow:

```text
completed -> running
completed -> ready
completed -> sleeping
archived -> running
archived -> ready
archived -> sleeping
waiting_approval -> running without approval_granted causality
blocked -> running without run_unblocked causality
failed -> running without retry/recovery event
```

Also forbidden:

```text
any transition without Event Record
any transition without actor Identity
any transition without Authority
any transition that crosses Project Run boundaries accidentally
any scheduler transition without causal trigger
```

## Transition record

A future transition record or enriched Event Record should answer:

```text
run_id
from_status
to_status
event_id
actor_identity_id
authority_basis
parent_event_id
transition_reason
timestamp
```

This is where execution and governance meet:

```text
Project Run state changed.
Event caused it.
Causality explains it.
Identity acted.
Authority permitted it.
```

## Event mapping

Suggested lifecycle event mapping:

| Transition | Required event pattern |
|---|---|
| none -> created | `run_created` |
| created -> ready | `run_admitted` or future equivalent |
| ready -> running | `project_run_resumed` |
| sleeping -> running | `project_run_resumed` |
| running -> sleeping | `project_run_slept` or `checkpoint_saved` plus sleep intent |
| running -> completed | `project_run_completed` |
| running -> failed | future `project_run_failed` |
| any active state -> blocked | `run_blocked` |
| blocked -> ready | `run_unblocked` |
| blocked -> waiting_approval | `approval_requested` |
| waiting_approval -> ready/running | `approval_granted` -> `run_unblocked` or resume event |
| active/waiting state -> archived | future `project_run_archived` |

Current Event Type catalog does not include every future event named here. That
is fine. The state machine identifies the missing vocabulary before enforcement.

## Approval-gated transitions

Approval-sensitive transitions require an approval chain.

Example:

```text
running -> waiting_approval
  caused_by: approval_requested

waiting_approval -> ready
  caused_by: approval_granted -> run_unblocked

ready -> running
  caused_by: project_run_resumed
```

The approval grant must be attributable to an identity with approval authority.
An agent must not self-approve the transition that frees itself. Cute, but no.

## Blocked transitions

A blocked run needs explicit evidence to unblock.

```text
blocked -> ready
```

requires:

```text
run_unblocked
parent_event_id pointing to the blocker or resolution evidence
authorized actor identity
```

A blocked run should not jump directly to `running` unless the resume event is
causally downstream of the unblock event.

## Scheduler constraints

The scheduler does not own the state machine. It obeys it.

A scheduler may eventually propose or perform:

```text
ready -> running
waiting_event -> ready
sleeping -> ready
running -> sleeping
stale running -> blocked or suspended
```

But it must not:

```text
wake archived runs
resume completed runs
bypass waiting_approval
bypass blocked evidence
allocate a lease for a non-runnable state
invent authority
invent causality
```

Scheduler decisions must include:

```text
triggering Event Record
legal from_status -> to_status
actor/system identity
authority basis
resulting Event Record
```

## Runnable states

Potentially runnable:

```text
ready
sleeping
waiting_event after its awaited event arrives
waiting_approval after approval is granted
blocked after unblock evidence exists
failed after retry/recovery authorization
```

Not runnable:

```text
running
completed
archived
suspended unless resumed by authority
waiting_approval without approval
blocked without unblock evidence
```

## Read-only observability

Read-only views must report state, not change it.

```text
/project run list
/project run inspect <run_id>
/project run events <run_id>
/project event trace <event_id>
/project run why <run_id>
```

These commands may explain why a run is in a state. They must not repair illegal
states, append transition events, or silently normalize lifecycle mistakes.

## Constitutional invariants

```text
Every Project Run has exactly one current state.
Every state transition is caused by an Event Record.
Every state transition is attributable to an Identity.
Every state transition requires Authority.
Every state transition follows the legal transition graph.
Every scheduler state change obeys the state machine.
Terminal states are not resumable by default.
Read-only views do not mutate lifecycle state.
```

## Implementation details

These are not constitutional:

```text
string statuses vs enum objects
JSON store vs SQLite
exact event_id format
whether transition history is separate from Event Records
whether `ready` is persisted or computed
whether `running` means lease-held or operator-focused
exact scheduler priority scoring
```

Do not confuse the storage representation with the lifecycle law.

## Creation-time validation targets

Future write paths should validate:

| Write path | Validation |
|---|---|
| create run | initial state is legal and emits `run_created` |
| set status | from/to transition is legal |
| resume run | source state is runnable and event causality exists |
| block run | blocker event exists and actor has authority |
| unblock run | unblock event cites blocker/resolution evidence |
| request approval | transition to `waiting_approval` is legal |
| grant approval | approver identity has authority and is not requester |
| complete run | source state allows completion |
| archive run | archival authority exists and terminal semantics are preserved |
| scheduler wake | run state is runnable and triggering event exists |

## Read-only validator

The first court of Project OS is:

```text
/project validate
```

It reports PASS/FAIL and violations with affected `run_id`, `event_id`, the law
violated, and a detail string. It must not mutate, repair, normalize, backfill,
or auto-fix state. Scenario case law lives in `PROJECT_OS_SCENARIOS.md`; reusable
rulings live in `PROJECT_OS_PRECEDENTS.md`; lawful responses live in
`PROJECT_OS_REMEDIES.md`.

## Non-goals

This document does not implement:

```text
mutating transition enforcement
automatic scheduler
Event Queue
Wake Policy
approval queue
Agent Lease allocation
new Event Types
status migration
state repair
```

It defines the legal lifecycle graph that future runtime writes and scheduler
policy must obey.
