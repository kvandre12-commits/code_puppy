# Kennel Distillation

The hardest part of durable project memory is not storage. It is distillation.
The system must continuously answer:

```text
What from today deserves to exist tomorrow?
```

Most conversations do not. Most notifications do not. Most transcripts do not.
Some facts do. Some decisions do. Some artifacts do. Some relationships do. Some
history does.

## Core flow

```text
Conversation
  -> Quarantine
  -> Typed Durable Memory
  -> Future Work
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
Facts
Decisions
Artifacts
Relationships
History
```

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
3. a policy or safety boundary;
4. a project object or artifact reference;
5. a relationship needed for orchestration;
6. a history event needed for audit/replay.

Otherwise leave it in quarantine and prune later.

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
Project Operating System running on top of Android.
