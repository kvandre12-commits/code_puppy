# Project OS Runtime

The kennel defines what deserves to survive. The runtime defines what can keep
executing. The scheduler doctrine lives in `PROJECT_OS_SCHEDULER.md`.

The knowledge ontology is now:

```text
Project
  -> Objectives
  -> Work Items
  -> Principles
  -> Facts
  -> Decisions
  -> Artifacts
  -> Relationships
  -> History
```

That is necessary, but not sufficient for an operating system. A Project OS also
needs a runtime object between Projects and Agents.

```text
Linux      -> Process
Android    -> Activity / Task
Project OS -> Project Run
```

## Kernel object: Project Run

A **Project Run** is the resumable execution context for a project objective.
It is not an agent, not a model, not a chat session, and not raw memory.

It binds:

```text
project
objective
selected work items
loaded institutional knowledge
capability grants
agent leases
checkpoint
journal
next action
```

The Project persists. Objectives change. Work items complete. Agents attach and
detach. Models are swapped. The Project Run is the active or suspended execution
instance that makes continuity possible.

## Why Project is not enough

A Project answers:

```text
What durable operating unit are we continuing?
```

But it does not answer:

```text
What is currently executing?
Who is attached?
What is blocked?
What is the next action?
Which grants are active?
What checkpoint should a new agent load?
```

Those are runtime questions. They belong to a Project Run.

## Why Agent is not enough

Agents are workers. They should not be the source of truth for execution state.

An agent can disappear because:

```text
model changed
process crashed
phone rebooted
operator switched agents
provider failed
session expired
```

The Project Run must survive all of that.

Agents attach to Project Runs through leases, not ownership.

```text
Project Run
  -> Agent Lease
      -> agent name
      -> model name
      -> granted scopes
      -> heartbeat
      -> expiry
```

If the agent dies, the lease expires. The run remains.

## Project lifecycle

### 1. Create project

A durable Project is created or discovered.

Examples:

```text
Code Puppy
SharpEdge
DroidPuppy
Robinhood Bridge
```

Initial state:

```text
project id
project name
repo/location references
principles/facts/decisions/artifacts/history
open objectives
```

No agent has to be attached yet.

### 2. Define objectives

Objectives are goals inside the project.

Examples:

```text
Design memory ontology
Build kennel audit
Create provider system
Create Android bridge
```

Objectives can finish, split, be replaced, or be revived while the project
persists.

### 3. Open work items

Work Items define executable units under a project/objective.

```text
planned
ready
active
blocked
done
cancelled
```

Work Items are durable. Their current execution grouping belongs to a Project
Run.

### 4. Start or resume a Project Run

Starting a run creates a runtime object:

```text
run id
project id
objective ids
selected work item ids
status
priority
operator intent
required grants
loaded knowledge summary
checkpoint pointer
journal pointer
```

Resuming a run loads the latest checkpoint and recomputes the working context.

### 5. Attach agents

Agents attach to a Project Run with leases.

```text
run id
agent id/name
model name
role
scopes
timeout
heartbeat
```

Agents do not own the project. They do not own the objective. They do not own the
run. They hold a revocable execution lease.

### 6. Execute

During execution, agents may:

```text
advance work items
produce artifacts
request approvals
observe Android state
call tools within grants
write journal events
propose durable knowledge
checkpoint progress
```

The runtime records execution. The kennel distills what deserves permanence.

### 7. Suspend

A run can suspend because:

```text
operator stopped
approval pending
blocked dependency
phone reboot
agent/model failure
waiting for market/session/time
```

Suspension must write a checkpoint with enough state for a future agent to
continue.

### 8. Complete

A run completes when its selected work items/objective slice are done or
intentionally closed.

Completion should produce:

```text
final work item statuses
artifact references
journal summary
knowledge promotion candidates
next objective suggestions
```

### 9. Archive project

Project archival is not deletion.

Archival should preserve:

```text
project record
closed objectives
closed work items
artifacts
decisions
principles
history
run records
final checkpoints
```

Archival should not preserve live execution leases. A restored project starts a
new Project Run.

## Project Run table

The Project OS equivalent of a process table is a **Run Table**.

Minimum columns conceptually:

```text
run_id
project_id
objective_ids
work_item_ids
status
priority
created_at
updated_at
last_checkpoint_at
last_heartbeat_at
blocked_reason
next_action
owner/operator
active_agent_leases
required_capabilities
artifact_refs
journal_ref
```

Useful statuses:

```text
created
ready
running
waiting_approval
blocked
suspended
completed
failed
archived
```

The Run Table answers:

```text
What is executing?
What is resumable?
What is blocked?
Who is attached?
What needs operator approval?
What should be scheduled next?
```

A second table, the **Agent Lease Table**, answers:

```text
Which agents are attached to which runs?
Which scopes did they receive?
Are they alive?
When do their leases expire?
```

## Loading context for agents

Agents should load context from the Project Run, not directly from a pile of
memories.

Runtime context assembly:

```text
Project Run
  -> project identity
  -> active objective(s)
  -> selected work item(s)
  -> relevant principles
  -> relevant facts
  -> relevant decisions
  -> artifact handles
  -> relationships/dependencies
  -> recent history/journal summary
  -> grants and constraints
  -> next action
```

The agent receives a working set, not the universe.

This keeps context bounded and prevents the model from rediscovering the same
project state every time it wakes up.

## What survives replacement

### Agent replacement

Survives:

```text
Project
Objectives
Work Items
Project Run
checkpoint
journal
artifact refs
capability requirements
institutional knowledge
```

Does not survive:

```text
agent lease
hidden scratchpad
uncommitted tool intent
in-flight local variables
```

### Model replacement

Survives:

```text
every durable project object
Project Run state
checkpoint
journal
operator approvals
artifact refs
```

Does not survive:

```text
model-specific hidden reasoning
prompt cache
provider session state
```

The model is compute. It is not the project.

### Project archival

Survives:

```text
project manifest
closed objectives
closed work items
run records
final checkpoints
artifacts
decisions
principles
history
```

Does not survive as live state:

```text
active leases
active grants
running status
heartbeat expectations
```

A restored archived project should create a new Project Run, not pretend an old
run is still alive.

## Minimum resume state after months

To resume execution after months of inactivity, the Project OS needs at least:

```text
project id/name
project location/repo/artifact roots
active or selected objective
unfinished work items with status
last checkpoint summary
next action
blocked reason, if any
required approvals/grants
relevant principles
relevant decisions
artifact references
recent history/journal summary
operator constraints
```

Everything else can be recomputed or rediscovered. This set is the minimum
state that turns archaeology into resumption.

## Relationship to kennel

The kennel is not the scheduler. The kennel preserves durable institutional
knowledge and continuity material.

The Project Run is runtime state. It can ask the kennel for knowledge, and it can
produce new candidate knowledge, but it should not be replaced by the kennel.

```text
Project Run -> asks kennel: what does this project know?
Project Run -> updates work/journal/checkpoint
Project Run -> proposes durable drawers
Kennel      -> stores promoted institutional knowledge
```

That separation prevents memory from becoming a fake process manager.

## Design rule

Do not attach Agents directly to Projects for execution.

Attach Agents to Project Runs.

```text
Project
  -> Project Run
      -> Agent Lease
```

This is the core runtime boundary. It is the difference between:

```text
an agent remembering a project
```

and:

```text
a project continuing through replaceable agents
```
