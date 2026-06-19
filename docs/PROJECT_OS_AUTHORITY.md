# Project OS Authority

Project OS authority answers a different question than capability grants. It
rests on the identity doctrine in `PROJECT_OS_IDENTITY.md`.

Capability grants ask:

```text
What tool or bridge can this agent use?
```

Authority asks:

```text
Who is allowed to change Project OS state?
Who may approve?
Who may observe?
Who may delegate?
Who is accountable for the action?
```

This document is doctrine, not enforcement code. It defines the responsibility
layer future Project, Objective, Work Item, Event Queue, Scheduler, and Agent
Lease implementations must obey.

## Doctrine

```text
No direct power. Only granted power.
No authority without identity.
No action without attribution.
No state change without authority.
No authority without accountability.
No delegation without scope.
```

Related Project OS doctrines:

```text
Evidence first. Behavior second.
Laws before policy.
Validation before automation.
No scheduling without causality.
No causality without events.
No events without observability.
```

## Authority is not capability

An agent might have a tool grant to write a file or launch an Android intent.
That does not automatically mean the agent is authorized to change a Project
Objective, complete a Work Item, approve a blocked Run, or allocate a lease.

```text
Capability = can technically perform an operation
Authority  = may legitimately perform that operation
```

Both must be true before sensitive state changes occur.

## Core roles

These are conceptual roles. They may eventually be backed by user IDs, agent IDs,
scoped tokens, local config, or a project authority table. The implementation
shape is not constitutional. The authority boundaries are.

### Project Owner

The Project Owner is accountable for the Project.

May:

```text
create Project
archive Project
assign or revoke Maintainers
approve high-impact delegation
approve destructive project-level changes
set authority policy for the Project
```

Must not be silently replaced by an agent, model, provider session, or scheduler.

### Project Maintainer

A Project Maintainer can shape project structure inside owner-defined bounds.

May:

```text
create Objective
change Objective
create Work Item
move Work Item between Objectives
mark Work Item complete
create Project Run for authorized Objectives
record non-approval Event Records
```

May not:

```text
change Project ownership
approve actions reserved for Owner
grant unbounded authority to agents
bypass Event Records for structural changes
```

### Operator

The Operator is the human currently steering execution.

May:

```text
inspect state
request Project Run creation
checkpoint or suspend a run when authorized
approve or reject approval requests assigned to them
resume a run when policy allows
choose active focus
```

The Operator is often the Owner in single-user local mode, but those concepts
should remain separate. Future multi-user or delegated workflows will need the
separation. Yes, future-us will complain. Future-us can cope.

### Agent

An Agent is a worker attached through a lease or explicitly granted scope.

May:

```text
observe permitted state
record evidence it is authorized to record
execute leased work within scope
propose Objective or Work Item changes
request approval
checkpoint its assigned run
```

May not:

```text
own Project
own Project Run
self-approve privileged actions
grant itself authority
allocate its own lease
silently wake arbitrary runs
complete Work Items outside delegated scope
```

### Observer

An Observer can inspect but not mutate Project OS state.

May:

```text
/project run list
/project run inspect <run_id>
/project run events <run_id>
/project run event-types
/project event trace <event_id>
/project run why <run_id>
```

May not:

```text
create Project Run
change Objective
complete Work Item
record Event Record
approve request
allocate lease
```

## Authority matrix

This is the conceptual baseline. Concrete projects may narrow authority, but
should not widen it silently.

| Action | Owner | Maintainer | Operator | Agent | Observer |
|---|---:|---:|---:|---:|---:|
| Create Project | yes | delegated | no | no | no |
| Archive Project | yes | delegated | no | no | no |
| Create Objective | yes | yes | request | propose | no |
| Change Objective | yes | yes | request | propose | no |
| Create Work Item | yes | yes | request | propose | no |
| Complete Work Item | yes | yes | delegated | delegated | no |
| Create Project Run | yes | yes | delegated | no/self only if leased policy allows | no |
| Checkpoint Project Run | yes | yes | delegated | leased run only | no |
| Mark Run blocked | yes | yes | delegated | request/record evidence | no |
| Mark Run unblocked | yes | yes | delegated | no without approval chain | no |
| Request approval | yes | yes | yes | yes if leased/delegated | no |
| Grant approval | yes | delegated | assigned approvals only | no self-approval | no |
| Allocate Agent Lease | yes | delegated | delegated | no | no |
| Revoke Agent Lease | yes | delegated | delegated | no | no |
| Observe state | yes | yes | yes | scoped | yes |

## Object authority

### Project

A Project is the top-level accountability boundary.

Invariant:

```text
Project authority is rooted in a Project Owner.
```

Questions every Project write must answer:

```text
Who requested the change?
Who had authority?
What Event Record proves it?
Was approval required?
```

### Objective

Objectives define what the Project Run is trying to accomplish.

Invariant:

```text
Objective changes require Owner or Maintainer authority, or an explicit delegated request.
```

Changing an Objective should emit:

```text
objective_changed
```

An agent may propose an Objective change. Proposal is not approval. Shocking, I
know.

### Work Item

Work Items are actionable units under Objectives.

Invariant:

```text
Completing a Work Item requires Maintainer, Operator-delegated, or Agent-leased authority.
```

Completion should emit:

```text
work_item_completed
```

### Project Run

Project Runs are resumable execution contexts, not agent-owned sessions.

Invariant:

```text
Project Run mutation requires authority derived from the Project and Objective.
```

Examples:

```text
checkpoint -> leased Agent or authorized Operator
resume     -> authorized Operator or future Scheduler with causal event
block      -> Maintainer/Operator or evidence-recording Agent request
unblock    -> authority plus causal evidence
```

### Event Record

Event Records are evidence. Evidence can be recorded by different actors, but the
record must say who did it.

Invariant:

```text
Every Event Record must have a source.
```

Source is not full identity yet, but it is the minimum accountability hook.
Future implementations should separate:

```text
source system
actor id
authority role
```

### Approval

Approval is not a vibe. Approval is an authority-bearing action.

Invariant:

```text
An approval_granted event must be attributable to an actor with approval authority.
```

An agent must not approve its own request for privileged action. That way lies
robot raccoon monarchy.

### Agent Lease

Agent Leases are delegated execution authority.

Invariant:

```text
An Agent Lease cannot exist without a Project Run and an authority grant.
```

A lease should define:

```text
run_id
agent identity
model/provider context if relevant
granted scopes
authorized actions
issued_by
issued_at
expires_at
revocation path
```

## Scheduler authority

The future scheduler is not sovereign. It is a policy engine operating under
Project authority.

The scheduler may eventually:

```text
wake a run
mark a run ready
request an agent lease
allocate a lease
expire stale leases
request approval
```

But every scheduler action must be explainable through:

```text
authority policy
triggering Event Record
causality trace
resulting Event Record
```

A scheduler must not:

```text
wake arbitrary runs without a causal event
allocate leases without authority
approve its own blocked actions
complete work without delegated authority
turn timestamps into causes
```

## Delegation

Delegation grants a narrower actor permission to act within explicit boundaries.

Valid delegation should specify:

```text
who delegates
who receives authority
what object scope applies
what actions are allowed
what expiration applies
what event records audit the delegation
how it can be revoked
```

Delegation must be narrower than or equal to the delegator's authority. If a
Maintainer cannot archive a Project, they cannot delegate archival authority to
an agent. This is apparently not obvious to software, so we write it down.

## Approval chains

Approval should become an Event causality chain.

Example:

```text
approval_requested
  -> approval_granted
      -> run_unblocked
          -> project_run_resumed
```

The chain answers:

```text
Who requested approval?
Who granted it?
What did it unblock?
What action happened next?
```

This is why causality exists before scheduling.

## Read-only authority

Observation is still authority, but lower-risk.

Read-only commands should be available to Observers unless project policy says
otherwise:

```text
list
inspect
events
event-types
trace
why
```

Read-only authority must not become mutation authority by accident. A view command
that appends events is not a view command. It is a raccoon in a trench coat.

## Creation-time validation targets

Future write paths should validate both structural invariants and authority.

| Action | Authority validation |
|---|---|
| Create Project | actor can act as Owner |
| Create Objective | Owner/Maintainer/delegated Operator |
| Change Objective | Owner/Maintainer/delegated Operator plus `objective_changed` event |
| Complete Work Item | Maintainer/delegated Operator/leased Agent plus `work_item_completed` event |
| Create Project Run | authority for Project and Objective |
| Record Event | actor allowed to record that Event Type for that Run |
| Grant Approval | actor assigned or allowed approval authority |
| Allocate Lease | actor/scheduler has lease allocation authority |
| Revoke Lease | actor/scheduler has revocation authority |
| Wake Run | triggering Event Record and authorized wake policy |

## Constitutional vs implementation detail

Constitutional:

```text
Authority is required for state mutation.
Authority must be accountable.
Delegation must be scoped.
Agents do not own Projects or Runs.
Schedulers execute policy; they do not create authority.
Approvals require authorized actors.
Leases require delegated authority.
```

Implementation detail:

```text
role names in config vs database
single-user mode mapping Owner=Operator
exact authority file format
whether authority is local-only or synced
how actor identity is represented
how approval assignment is routed
how delegation expiration is stored
```

Do not confuse today's local phone workflow with the constitutional model.
Single-user mode can collapse roles operationally, but the architecture should
not erase the distinction.

## Non-goals

This document does not implement:

```text
authentication
authorization middleware
role storage
approval queue
Event Queue
Scheduler
Agent Lease Allocation
multi-user sync
cryptographic identity
```

It defines who may act before the system grows more ways to act.
