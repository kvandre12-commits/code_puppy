# Project OS Scheduler

The Project OS has a durable object:

```text
Project
```

and a runtime object:

```text
Project Run
```

Once multiple Project Runs exist, the next kernel service is scheduling.

```text
Linux      -> scheduler chooses processes/threads for CPU
Android    -> ActivityManager/JobScheduler choose app work
Project OS -> Run Scheduler chooses Project Runs for Agents
```

The scheduler is not memory. It is not an agent. It is not a model. It is the
policy service that decides what gets execution attention next.

## Core model

```text
Projects
  -> Project Runs
      -> Agent Leases
          -> Agents
              -> Models
```

The eventual event-driven execution loop is:

```text
Event Record -> Event Queue -> Wake Run -> Lease Agent -> Execute -> Checkpoint -> Sleep
```

Scheduling turns resumable runs into an operating system, but scheduling must not
come before observability.

```text
Event Record -> Event Queue -> Run Table -> priority -> lease allocation -> checkpoint
```

Doctrine:

```text
No execution without observability.
No observability without events.
```

Durability boundary:

```text
Project/Project Run/Knowledge survive.
Agent Lease/Agent/Model/Provider session are disposable.
```

## Kernel service: Run Scheduler

The **Run Scheduler** owns runtime policy:

```text
which Project Runs are runnable
which runs are blocked
which runs are waiting on approval
which agents are available
which leases should be issued
which leases should be revoked
which run should wake next
```

It does not own project knowledge. It asks the Project Run and kennel for the
working set needed by an agent.

## Scheduler inputs

The scheduler observes:

```text
Run Table
Agent Lease Table
Event Queue
Approval Queue
Capability/Grant state
Android/device state
operator focus
project priorities
work item status
calendar/time/session constraints
```

Examples:

```text
SharpEdge market run wakes at market open.
Robinhood Bridge run blocks on operator approval.
DroidPuppy run waits for ADB reconnect.
Code Puppy doc run is ready immediately.
```

## Scheduler outputs

The scheduler emits:

```text
create Project Run
resume Project Run
suspend Project Run
allocate Agent Lease
revoke Agent Lease
mark blocked
mark waiting_approval
wake on event
request operator decision
checkpoint now
```

## Run states

A Project Run should have explicit states:

```text
created
ready
running
waiting_event
waiting_approval
blocked
suspended
completed
failed
archived
```

Meaning:

| State | Meaning |
|---|---|
| `created` | Run exists but has not passed readiness checks |
| `ready` | Run can receive an Agent Lease |
| `running` | One or more active leases exist |
| `waiting_event` | Dormant until a wake event arrives |
| `waiting_approval` | Blocked on operator/governance approval |
| `blocked` | Cannot proceed until dependency is resolved |
| `suspended` | Intentionally paused with checkpoint |
| `completed` | Selected objective/work slice is done |
| `failed` | Run hit unrecovered error and needs triage |
| `archived` | Historical only; not schedulable |

## Event Record before Event Queue

Before an Event Queue exists, the Project OS must persist Event Records. Records
are durable evidence; queues are scheduling machinery. Do not build behavior
before the evidence trail exists.

Event Types are the stable vocabulary between records and scheduling policy:

```text
lifecycle -> run_created, checkpoint_saved, project_run_resumed, project_run_slept, project_run_completed
work      -> work_item_completed, objective_changed, artifact_created
governance-> approval_requested, approval_granted
blocking  -> run_blocked, run_unblocked
```

The future scheduler should react to these typed facts, not infer state from
free-form prose.

## Event Queue

The Project OS equivalent of wakeup interrupts is an **Event Queue**. It is a
kernel service, not a side list. The scheduler should react to queued events,
not poll runs forever like a bored intern.

Events may come from:

```text
operator command
Git commit or PR merged
file/repo change
timer/calendar
Android notification
Android app state
browser state
broker/market alert
work item completed
project run stalled
approval decision
agent heartbeat timeout
capability grant change
network/device reconnect
```

Event shape conceptually:

```text
event_id
event_type
source
project_id
run_id optional
objective_id optional
work_item_id optional
payload/ref
time
priority hint
```

The scheduler consumes events and decides whether they wake, create, requeue, or
ignore a run.

## What wakes a dormant Project Run

A dormant run can wake when:

```text
operator resumes it
scheduled time arrives
approval is granted
blocked dependency clears
required device capability appears
agent lease becomes available
file/artifact changes
external signal arrives
fresh observation invalidates old checkpoint
```

Examples:

```text
ADB reconnect wakes DroidPuppy support run.
Market open wakes SharpEdge cockpit run.
Approval grant wakes Robinhood order-draft handoff run.
GitHub change wakes Code Puppy review run.
```

Wakeups should not imply immediate execution. They move a run into `ready` or
`created`; priority and resource checks still apply.

## What suspends a Project Run

A run should suspend when:

```text
operator pauses it
agent lease expires
agent/model fails
required approval is missing
required grant is revoked
required Android/device state disappears
work item becomes blocked
run exceeds budget/timebox
checkpoint requested
higher-priority run preempts it
```

Suspension requires a checkpoint. If there is no checkpoint, the scheduler should
mark the run `failed` or `blocked`, not pretend it is safely resumable.

## Priority model

Priority should be explicit and boring. Fancy priority magic is where project
OSes become haunted slot machines.

A simple score can start with:

```text
operator_priority
+ due_time_pressure
+ unblock_value
+ active_user_focus
+ stale_age
+ dependency_fanout
- approval_wait_penalty
- blocked_penalty
- risk_penalty
- resource_cost
```

Priority inputs:

| Input | Meaning |
|---|---|
| operator priority | Human says this matters |
| due time pressure | Deadline/session window is near |
| unblock value | Other work depends on this run |
| active focus | User is currently working in this project |
| stale age | Ready run has waited too long |
| dependency fanout | Completing it unblocks many items |
| approval wait | Cannot proceed without decision |
| blocked penalty | Known dependency missing |
| risk penalty | Destructive/trading/device mutation risk |
| resource cost | Expensive model/tool/device use |

Minimum policy:

```text
approval-gated runs never auto-execute writes
blocked runs never receive execution leases
operator-pinned runs beat normal runs
aging prevents starvation
risk lowers automation level
```

## Lease allocation

Agents are allocated by lease, not ownership.

```text
Run Scheduler
  -> selects ready Project Run
  -> selects capable Agent
  -> grants scoped Agent Lease
  -> assembles run context
  -> starts/resumes execution
```

Lease fields conceptually:

```text
lease_id
run_id
agent_name
model_name
role
scopes
issued_at
expires_at
heartbeat_at
revoked_at optional
```

A lease should expire or be revoked when:

```text
heartbeat missing
run suspends/completes/fails
operator revokes
scope revoked
agent misbehaves/errors
timebox exceeded
higher-priority interrupt requires preemption
```

## Multiple agents on one Project Run

Multiple agents can lease the same Project Run only if roles are explicit.

Good examples:

```text
planner lease
coder lease
qa lease
android-observer lease
support-bundle lease
```

Bad example:

```text
three agents all mutate the same files with no coordinator
```

Concurrency rule:

```text
one writer per artifact/work item unless an explicit coordinator exists
many readers allowed
approval-gated actions require single accountable lease
```

The scheduler should prefer serialized mutation until conflict handling exists.
Do not cosplay Kubernetes before the bicycle has wheels.

## Approval and blocker modeling

Approvals are scheduler-visible wait states, not chat messages.

```text
Project Run
  -> waiting_approval
      -> approval_request_id
      -> requested_action
      -> risk tier
      -> required operator
      -> expires_at optional
```

Blockers are also first-class wait states:

```text
Project Run
  -> blocked
      -> blocker_type
      -> blocker_ref
      -> unblock_event
      -> owner optional
```

Examples:

```text
waiting_approval: submit broker order
blocked: ADB wireless debugging disconnected
blocked: GitHub credentials missing
waiting_event: market opens at 9:30
```

The scheduler wakes runs when approvals or unblock events arrive.

## Equivalent of ps, top, and task manager

The Project OS needs operator-visible runtime views.

### ps equivalent: run list

```text
run_id  project     objective        state              next_action
r42     Code Puppy  scheduler doc    running            draft doctrine
r43     SharpEdge   market cockpit   waiting_event      market open
r44     DroidPuppy  adb reconnect    blocked            wireless debugging
r45     Robinhood   broker bridge    waiting_approval   order handoff
```

### top equivalent: run monitor

Shows live scheduling pressure:

```text
priority
state
lease count
last heartbeat
blocked reason
approval wait age
next wake time
resource/model usage
```

### task manager equivalent: run control

Operator actions:

```text
pause run
resume run
cancel run
bump priority
lower priority
reassign agent
revoke lease
grant approval
reject approval
archive completed run
```

## Reboot survival

The scheduler itself does not need to survive as an in-memory process. Scheduler
state must be reconstructable.

After device reboot:

```text
load Run Table
load Agent Lease Table
expire leases with missing heartbeat
load pending events/approvals
mark previously running runs as suspended_or_ready
recompute priorities
wake eligible runs
wait for operator if needed
```

No run should assume an old agent is still alive after reboot.

Reboot rule:

```text
Project Runs survive.
Agent Leases do not.
Agents/models/providers do not own continuity.
Scheduler decisions are replayed/recomputed.
```

## Agent replacement

When an agent disappears:

```text
lease heartbeat expires
scheduler revokes lease
run returns to ready/blocked/suspended based on checkpoint
new capable agent may lease the run
context reloads from Project Run + kennel
```

The replacement agent should receive:

```text
run summary
checkpoint
open work item
next action
constraints/grants
recent journal
relevant institutional knowledge
```

Not the dead agent's hidden scratchpad. That thing is compost.

## Model replacement

When a model changes:

```text
lease updates or expires
run checkpoint stays
context is reassembled
model-specific prompt/session state is discarded
```

The scheduler should treat model choice as a lease attribute, not project truth.

## Scheduling policies

Start with conservative policies:

```text
operator-pinned first
ready before waiting
blocked never scheduled
approval waits never bypassed
single writer per artifact
short safe runs may batch
aging prevents starvation
risk requires stronger approval
```

Avoid autonomous background chaos. The scheduler should be boring, inspectable,
and interruptible.

## Relationship to Android

Android owns device scheduling, app lifecycle, power, notifications, and
permissions. Code Puppy should not fight that.

The Run Scheduler should adapt to Android:

```text
battery low -> reduce background runs
network absent -> block network-dependent runs
ADB absent -> block Android-observation runs
notification arrives -> enqueue event
operator opens project -> boost focused run
```

Android schedules apps and services. Code Puppy schedules project execution.

## Relationship to kennel

The kennel answers:

```text
What does this project know?
```

The Run Scheduler answers:

```text
What should run next, and which event woke it?
```

Project Run bridges them:

```text
Run Scheduler -> picks run
Project Run   -> defines execution context
Kennel        -> supplies institutional knowledge
Agent Lease   -> grants replaceable worker execution rights
```

## Minimal scheduler state

Minimum state to resume scheduling after months:

```text
run table
agent lease table, with stale leases expirable
pending event queue
pending approval queue
project priorities
blocked reasons
next wake times
last checkpoints
operator constraints
capability/grant state
```

Everything else can be recomputed from projects, runs, kennel, and Android
observation.

## Design rule

Do not let agents self-schedule by vibes.

```text
Project Run = what can execute
Run Scheduler = what should execute next
Agent Lease = who may execute it temporarily
```

That is the boundary that turns Project Runs into a Project OS instead of a pile
of ambitious todos.
