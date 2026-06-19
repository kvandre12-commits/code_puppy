# Project OS Scenarios

Project OS has enough constitutional doctrine to start hearing cases.

This document records scenario stories that exercise the model end-to-end:

```text
Constitution -> Court -> Case Law
```

The court is:

```text
/project validate
```

Scenarios should answer one question:

```text
Can the system consistently recognize a legal story from an illegal story?
```

## What scenario tests are for

Unit tests check one clause at a time. Scenario tests check whether Project OS
objects, events, causality, identity, authority, lifecycle state, and validation
work together as a coherent story.

A scenario should include:

```text
initial Project Run state
Event Record sequence
causality links when relevant
actor/source attribution
expected validator judgment
```

Scenario tests live in:

```text
tests/test_project_os_scenarios.py
```

Reusable rulings live in:

```text
PROJECT_OS_PRECEDENTS.md
```

## Scenario 1: Approval Gate

Precedent:

```text
PRECEDENT-001
```

Expected judgment:

```text
PASS
```

Story:

```text
run_created
  -> approval_requested
      -> approval_granted
          -> run_unblocked
              -> project_run_resumed
```

Why legal:

```text
approval was requested
approval was granted by an attributable source
unblock is causally downstream of approval_granted
resume is causally downstream of run_unblocked
current running status has project_run_resumed evidence
```

This scenario establishes case law that `approval_granted -> run_unblocked` is a
valid unblock chain even without a separate `run_blocked` event. Approval itself
can be the thing being unblocked.

## Scenario 2: Illegal Blocked Resume

Precedent:

```text
PRECEDENT-002
```

Expected judgment:

```text
FAIL
```

Story:

```text
run_created
  -> run_blocked
      -> project_run_resumed
```

Why illegal:

```text
blocked run resumed without run_unblocked evidence
resume is causally downstream of blocker, not resolution
```

Validator law:

```text
A blocked run cannot resume without run_unblocked causality.
```

## Scenario 3: Project Continuity

Precedent:

```text
PRECEDENT-006
```

Expected judgment:

```text
PASS
```

Story:

```text
Project Run created
  -> checkpoint_saved
  -> agent replaced
  -> model replaced
  -> project_run_resumed
```

Why legal:

```text
Project Run persists independent of agent/model
checkpoint evidence exists
resume evidence exists
current running status has project_run_resumed evidence
```

This scenario protects the durability boundary:

```text
Project/Project Run/Knowledge survive.
Agent/Model/Provider session are disposable.
```

## Scenario 4: Governance Failure

Precedent:

```text
PRECEDENT-003
```

Expected judgment:

```text
FAIL
```

Story:

```text
run_created
  -> approval_requested
      -> approval_granted with empty source
```

Why illegal:

```text
approval has no attribution hook
actor identity cannot be reconstructed later
approval authority cannot be audited
```

Validator law:

```text
Every Event Record must have source attribution.
```

Current implementation note: `source` is not full actor identity yet. It is the
minimum attribution hook until Event Records grow structured identity fields.

## Scenario doctrine

```text
Legal stories should PASS.
Illegal stories should FAIL.
Ambiguous stories should become either explicit law or explicit non-goals.
No scenario should require scheduler, queue, wake policy, or lease allocation.
```

## Non-goals

Scenarios do not implement:

```text
Scheduler
Event Queue
Wake Policy
Agent Lease allocation
approval queue
identity storage
authority middleware
state repair
```

They exercise what already exists so the model feels operational pressure before
more machinery is added.
