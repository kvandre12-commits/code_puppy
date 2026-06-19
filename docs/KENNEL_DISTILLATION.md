# Kennel Distillation

The hardest part of durable project memory is not storage. It is distillation.
This is where memory architecture becomes knowledge economics architecture.
The system must continuously answer:

```text
What from today deserves to exist tomorrow?
```

Most conversations do not. Most notifications do not. Most transcripts do not.
Some projects do. Some objectives do. Some work items do. Some principles do.
Some facts do. Some decisions do. Some artifacts do. Some relationships do. Some
history does.

The kennel is not just storing memory. It is converting work into institutional
knowledge and institutional continuity.

## Core flow

```text
Conversation
  -> Quarantine
  -> Distillation
  -> Typed Durable Memory
  -> Future Work
```

A broader Project OS stack:

```text
Human
  -> Projects
  -> Objectives
  -> Work
  -> Institutional Knowledge
  -> Agents
  -> Android
  -> Linux
```

Agents should stop asking:

```text
What was in that conversation?
```

and start asking:

```text
Which project are we continuing?
What are we trying to accomplish?
What have we learned?
What remains unfinished?
```

Raw transcript is allowed into the kennel only as temporary quarantine. It must
then be distilled into typed durable drawers or pruned.

```text
quarantine transcript
  -> distill typed drawers
  -> promote durable drawers
  -> prune transcript crumbs
```

## Project-rooted durable memory and work

Organizations do not preserve knowledge for its own sake. They preserve
knowledge in service of projects and goals. They also preserve the execution
state needed to continue those goals. Without a project, drawers become isolated
facts attached to nothing durable. With a project, objectives, and work items,
they become a continuity graph.

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

Example:

```text
Project: Code Puppy
  -> Objective: Build Android Project OS
  -> Work Item: Implement kennel audit. Status: done.
  -> Work Item: Implement distillation agent. Status: planned.
  -> Principle: Do not fight Android.
  -> Fact: Android owns permissions.
  -> Decision: Use quarantine before promotion.
  -> Artifact: docs/ANDROID_AGENT_OS_LAYER.md
```

The kennel's job is knowledge governance. The real question is not merely:

```text
What happened?
```

It is:

```text
What deserves to survive,
for which project,
for which objective,
and what remains unfinished?
```

## Durable drawer types

```text
Projects
Objectives
Work Items
Principles
Facts
Decisions
Artifacts
Relationships
History
```

### Projects

Long-lived operating units. Projects endure across sessions, agents, models,
objectives, and individual developers. They are the root objects for durable
execution and knowledge.

Examples:

```text
Code Puppy.
SharpEdge.
DroidPuppy.
Robinhood Bridge.
```

### Objectives

Goals inside a project. Objectives can finish, change, or be replaced while the
project persists.

Examples:

```text
Design memory ontology.
Build kennel audit.
Create provider system.
Create Android bridge.
```

### Work Items

Execution units attached to an objective. Work items answer what is planned,
active, blocked, or done. They are not principles and they are not history;
history records how they changed over time.

Examples:

```text
Implement kennel audit. Status: done.
Implement distillation agent. Status: planned.
Add objective/work filters to recall. Status: planned.
```

A future agent should be able to attach to a project and objective, load durable
knowledge, inspect unfinished work items, and continue execution without needing
the original conversation or the original person.

### Principles

Governing rules used to judge future work. Principles are stronger than ordinary
decisions because they constrain future decisions.

Examples:

```text
No direct power. Only granted power.
Do not fight Android.
Quarantine before promotion.
```

Principles need tiers or they inflate into noise:

```text
Principles
  -> Constitutional
  -> Operational
  -> Deprecated
```

Constitutional principles govern the whole OS. Operational principles govern a
specific project, subsystem, or workflow. Deprecated principles are retained for
history and audit, but should not guide new work.

A candidate principle should not be promoted unless it is:

1. broad enough to judge future work;
2. stable across more than one session;
3. clearer than the decision or fact it would replace;
4. worth enforcing or checking later.

If everything becomes a principle, no principle matters. This is principle
inflation, and it is institutional knowledge rot with a fancy hat.

### Facts

Something true about the system until changed.

Examples:

```text
Android owns runtime permissions.
ADB provider exists.
broker.robinhood exposes broker.read.
```

### Decisions

Something chosen as policy, direction, or architecture.

Examples:

```text
No god-agent.
Broker actions require approval.
Do not fight Android.
```

### Artifacts

Something produced by the work.

Examples:

```text
docs/AGENT_ORG_CHART.md
docs/ANDROID_AGENT_OS_LAYER.md
commit df737cb
commit 3f424fc
```

### Relationships

How project objects connect.

Examples:

```text
DroidPuppy depends on Android.
Chief Agent Officer supervises QA.
broker.robinhood is a provider.
```

### History

What happened over time.

Examples:

```text
Decision created.
Decision modified.
Decision revoked.
Commit pushed.
Quarantine distilled.
```

## Distillation rule

A large session should reduce to a small durable packet.

```text
57k-token session
  -> 1 project link
  -> 1 objective link
  -> 1 work item update
  -> 1 principle or policy check
  -> 1 fact
  -> 2 decisions
  -> 1 artifact
  -> 1 relationship
  -> 1 history entry
```

If a transcript produces no durable packet, the transcript should not keep
haunting future context. Searchable quarantine is useful briefly. Permanent chat
sludge is not.

## Selection criteria

Promote a drawer only if it is one of these:

1. reusable across future sessions;
2. expensive to rediscover;
3. tied to a project;
4. tied to an objective;
5. an execution state needed by future work;
6. a principle, policy, or safety boundary;
7. a project object or artifact reference;
8. a relationship needed for orchestration;
9. a history event needed for audit/replay.

Otherwise leave it in quarantine and prune later.

## Productivity versus activity

Yield metrics are not merely memory metrics. They are productivity metrics.

Example:

```text
SharpEdge session
  -> 1 project
  -> 1 objective
  -> 6 work item updates
  -> 2 principles
  -> 8 facts
  -> 12 decisions
  -> 25 artifacts
```

is different from:

```text
Another project
  -> 0 project link
  -> 0 objectives
  -> 0 work item updates
  -> 0 principles
  -> 1 fact
  -> 0 decisions
  -> 50 quarantine transcripts
```

The second project may be generating activity. The first is generating
institutional knowledge. Those are different outputs.

A chat log is personal memory. Institutional knowledge survives the person:

```text
architecture docs
runbooks
standards
decision records
policies
```

not raw chat transcripts.

## Distillation metrics

The future true metric is:

```text
Distillation Efficiency = Durable Drawers Created / Quarantine Drawers Processed
```

Yield can also be tracked by drawer type:

```text
Project Yield
Objective Yield
Work Item Yield
Principle Yield
Fact Yield
Decision Yield
Artifact Yield
Relationship Yield
History Yield
```

Today, until quarantine lifecycle events exist, audit output can only show a
proxy:

```text
observable durable ratio = durable notes / (durable notes + quarantine drawers)
distill backlog = quarantine drawers awaiting review
```

Do not confuse the proxy with true efficiency. True efficiency requires knowing
which quarantine drawers were processed, promoted, ignored, or pruned.

## Anti-token-burn engine

The point is not to save tokens. The point is to avoid repeatedly spending model
context on rediscovering the same operational truths.

```text
conversation volume down
signal density up
future work continuity up
```

The kennel becomes valuable only when the durable drawers are denser than the raw
conversation that produced them.

## Project OS consequence

If distillation works, Code Puppy gains persistent operational memory that
survives:

```text
app restarts
model swaps
provider changes
repo evolution
years of project history
```

At that point Code Puppy is no longer merely an AI coding assistant. It is a
Project Operating System running on top of Android, with institutional execution
and knowledge layers between projects, objectives, and agents.

## Constitutional docs

Some docs are no longer just notes. They are governing principles for future
work:

```text
KENNEL_DISTILLATION.md
ANDROID_AGENT_OS_LAYER.md
AGENT_ORG_CHART.md
AGENT_POWER.md
```

They define how future work is judged. The kennel should preserve this class of
knowledge as Principles, not bury it as generic facts or decisions.
