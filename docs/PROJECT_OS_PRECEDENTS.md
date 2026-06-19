# Project OS Precedents

Precedent answers a different question than causality.

```text
Causality: What caused this?
Precedent: Why is this allowed or forbidden?
```

Project OS now has three explanation graphs:

```text
Execution Graph:
Project -> Project Run -> Event Record -> Causality

Governance Graph:
Identity -> Role -> Authority -> Action

Legal Graph:
Scenario -> Ruling -> Precedent
```

The first court is:

```text
/project validate
```

The first casebook is:

```text
PROJECT_OS_SCENARIOS.md
```

This document records reusable rulings so future validator output, scheduler
refusals, and operator explanations can cite the reason a story is allowed or
forbidden.

## Doctrine

```text
Case Law before Automation.
Precedent explains validator judgment.
Causality explains what happened.
Precedent explains why the story is legal or illegal.
```

## Precedent registry

### PRECEDENT-001: Approval granted may legally unblock a run

Ruling:

```text
approval_granted may serve as valid evidence for a following run_unblocked.
```

Canonical story:

```text
approval_requested
  -> approval_granted
      -> run_unblocked
          -> project_run_resumed
```

Judgment:

```text
PASS
```

Reason:

```text
Approval itself can be the blocked condition being resolved.
A separate run_blocked event is not required when approval_requested is the gating event.
```

### PRECEDENT-002: Blocked runs may not resume without unblock evidence

Ruling:

```text
run_blocked followed by project_run_resumed is illegal without run_unblocked.
```

Canonical story:

```text
run_blocked
  -> project_run_resumed
```

Judgment:

```text
FAIL
```

Validator law:

```text
A blocked run cannot resume without run_unblocked causality.
```

### PRECEDENT-003: Event source attribution is mandatory

Ruling:

```text
approval and other Event Records must retain a non-empty source.
```

Canonical story:

```text
approval_requested
  -> approval_granted with empty source
```

Judgment:

```text
FAIL
```

Validator law:

```text
Every Event Record must have source attribution.
```

Current implementation note: `source` is the minimum attribution hook until Event
Records grow structured `actor_identity_id` fields. Yes, it is primitive. No,
that does not make it optional.

### PRECEDENT-004: Waiting-approval runs may not resume without approval granted

Ruling:

```text
approval_requested followed by project_run_resumed is illegal without approval_granted.
```

Canonical story:

```text
approval_requested
  -> project_run_resumed
```

Judgment:

```text
FAIL
```

Validator law:

```text
A waiting_approval run cannot resume without approval_granted causality.
```

### PRECEDENT-005: Terminal runs are not resumable by default

Ruling:

```text
project_run_completed makes later active lifecycle events invalid by default.
```

Canonical story:

```text
project_run_completed
  -> project_run_resumed
```

Judgment:

```text
FAIL
```

Validator law:

```text
Terminal states are not resumable by default.
```

### PRECEDENT-006: Project Runs survive agent and model replacement

Ruling:

```text
checkpointed Project Run state is durable across disposable workers.
```

Canonical story:

```text
Project Run created
  -> checkpoint_saved
  -> agent replaced
  -> model replaced
  -> project_run_resumed
```

Judgment:

```text
PASS
```

Reason:

```text
Project Run state persists independently of agent, model, and provider session.
```

## Validator citations

When `/project validate` reports a violation covered by precedent, it should cite
the precedent ID:

```text
law      : A blocked run cannot resume without run_unblocked causality.
precedent: PRECEDENT-002
detail   : project_run_resumed appears after blocker evt-...
```

Not every law has precedent yet. Missing precedent means the validator is citing
statute/doctrine only, not case law. That is allowed. The casebook should grow
from real scenarios, not speculative bureaucracy fan fiction.

## Non-goals

Precedents do not implement:

```text
Scheduler
Event Queue
Wake Policy
Agent Lease allocation
approval queue
identity storage
authority middleware
state repair
automatic enforcement
```

They explain court rulings before those rulings are used to automate behavior.
