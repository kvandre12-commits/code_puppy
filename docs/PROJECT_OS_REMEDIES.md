# Project OS Remedies

Remedy answers what should happen after the court finds a violation.

```text
Law -> Violation -> Precedent -> Remedy
```

This is not automatic repair. A remedy is the lawful response that future runtime
writes, schedulers, queues, and operators should respect.

```text
Validator PASS -> may proceed to the next policy layer
Validator FAIL -> do not proceed; apply the stated remedy
```

## Doctrine

```text
No automatic repair without explicit authority.
No scheduler bypass of validator remedies.
No mutation hidden inside validation.
Remedy constrains future behavior; it does not perform it.
```

Related explanation layers:

```text
Causality: what caused this?
Precedent: why is this allowed or forbidden?
Remedy: what should happen now?
```

## Remedy catalog

### REJECT_EVENT

Instruction:

```text
reject Event Record until its type, run, parent, and attribution are valid
```

Applies to examples like:

```text
unknown Event Type
missing Project Run
missing parent Event Record
causality cycle
malformed Event Record
```

### REQUIRE_ATTRIBUTION

Instruction:

```text
require a non-empty source before accepting the Event Record
```

This is the current minimal attribution remedy until structured actor identity is
persisted on Event Records.

### REJECT_TRANSITION

Instruction:

```text
reject transition until lifecycle evidence satisfies the state machine
```

Applies to examples like:

```text
blocked -> running without run_unblocked
completed -> running
illegal from_status -> to_status
```

### REQUIRE_APPROVAL

Instruction:

```text
require approval evidence before allowing the transition to proceed
```

Applies to examples like:

```text
waiting_approval -> running without approval_granted
approval_granted without approval_requested
```

### REQUIRE_EVIDENCE

Instruction:

```text
require causal Event Record evidence before accepting the state change
```

Applies to examples like:

```text
status running with no project_run_resumed event
run_unblocked without blocker or approval evidence
```

### MARK_INVALID

Instruction:

```text
mark state invalid for operator review; do not schedule or auto-repair
```

Applies to examples like:

```text
invalid run status
malformed Project Run
run_id mismatch
```

## Validator output

`/project validate` reports remedies when known:

```text
law      : A blocked run cannot resume without run_unblocked causality.
precedent: PRECEDENT-002
remedy   : REJECT_TRANSITION — reject transition until lifecycle evidence satisfies the state machine
detail   : project_run_resumed appears after blocker evt-...
```

The validator still does not apply the remedy. It reports the lawful response.

## Scheduler contract preview

A future scheduler should treat validation results as a gate:

```text
PASS -> scheduler may evaluate priority/policy
FAIL -> scheduler must not proceed; surface remedy
```

The scheduler must not invent its own remedy for known validator violations.
That would be cute in the way a raccoon in an evidence locker is cute.

## Non-goals

Remedies do not implement:

```text
automatic repair
scheduler
Event Queue
Wake Policy
Agent Lease allocation
approval queue
identity storage
authority middleware
state migration
```

They define the lawful response before response becomes automated behavior.
