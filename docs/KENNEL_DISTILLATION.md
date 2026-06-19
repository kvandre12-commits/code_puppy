# Kennel Distillation

The hardest part of durable project memory is not storage. It is distillation.
This is where memory architecture becomes knowledge economics architecture.
The system must continuously answer:

```text
What from today deserves to exist tomorrow?
```

Most conversations do not. Most notifications do not. Most transcripts do not.
Some principles do. Some facts do. Some decisions do. Some artifacts do. Some
relationships do. Some history does.

The kennel is not just storing memory. It is converting work into institutional
knowledge.

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
What does the institution know?
```

Raw transcript is allowed into the kennel only as temporary quarantine. It must
then be distilled into typed durable drawers or pruned.

```text
quarantine transcript
  -> distill typed drawers
  -> promote durable drawers
  -> prune transcript crumbs
```

## Durable drawer types

```text
Principles
Facts
Decisions
Artifacts
Relationships
History
```

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
3. a principle, policy, or safety boundary;
4. a project object or artifact reference;
5. a relationship needed for orchestration;
6. a history event needed for audit/replay.

Otherwise leave it in quarantine and prune later.

## Productivity versus activity

Yield metrics are not merely memory metrics. They are productivity metrics.

Example:

```text
SharpEdge session
  -> 2 principles
  -> 8 facts
  -> 12 decisions
  -> 25 artifacts
```

is different from:

```text
Another project
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
Project Operating System running on top of Android, with an Institutional
Knowledge Layer between projects and agents.

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
