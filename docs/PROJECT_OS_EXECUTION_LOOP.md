# Project OS Execution Loop

The governance stack is now strong enough to constrain behavior.

```text
Governance Stack:
Identity -> Authority -> Events -> Causality -> State Machine -> Validator -> Precedent -> Remedy

Runtime Stack:
Project -> Project Run -> Event Queue -> Scheduler -> Agent Lease -> Execution
```

This document defines the minimum runtime that can execute a legal Project Run.
It does not implement scheduling, queues, leases, wake policies, or execution.
It defines the smallest safe loop those future components must obey.

## Doctrine

```text
Governance is authoritative.
Runtime must obey governance.
Validator PASS is the runtime gate.
Validator FAIL applies remedy and stops execution.
No auto-repair.
No scheduler bypass.
No lease without authority.
No execution without a legal Project Run state.
```

The runtime exists to do work. The governance stack exists to stop work from
becoming cursed. Both are necessary; only one gets to say whether behavior is
legal. Spoiler: it is not the scheduler.

## Runtime boundary

The runtime stack should answer:

```text
What work is ready?
Which run should receive attention?
Who may execute it?
What authority/capability scope applies?
What event proves the result?
```

The runtime stack must not decide:

```text
whether an illegal transition is acceptable
whether attribution is optional
whether approval can be skipped
whether invalid state should be repaired silently
```

Those are governance questions.

## Minimum viable Event Queue

The smallest Event Queue is not a new source of truth. It is a scheduling view
over Event Records.

Minimum queue entry fields:

```text
queue_id
trigger_event_id
run_id
queue_state
available_at
priority_hint
created_at
claimed_by optional
claim_expires_at optional
```

Minimum states:

```text
pending
claimed
done
dead_letter
```

Read-only first version:

```text
Event Records -> queue candidate projection
```

This can be implemented before a mutable queue table. It would answer:

```text
Which Event Records could wake or schedule a run if validation passes?
```

Must remain impossible until validator PASS:

```text
enqueue invalid Event Record
claim work for invalid Project Run
turn validator FAIL into runnable work
hide a remedy behind queue state
```

## Minimum viable Scheduler

The smallest Scheduler is a selector, not an executor.

Read-only first version:

```text
Run Table + validator PASS + queue candidates -> scheduling candidates
```

It should answer:

```text
which Project Runs are eligible?
why are they eligible?
which Event Record made them eligible?
which state transition would be required next?
which remedy blocks ineligible runs?
```

Minimum scheduler candidate fields:

```text
run_id
current_status
trigger_event_id
candidate_reason
required_transition
validator_status
blocking_remedy optional
```

The scheduler must not:

```text
wake archived runs
resume completed runs
bypass waiting_approval
bypass blocked evidence
allocate leases without authority
invent causality
invent remedies
```

Mutable scheduling can come later. First, the scheduler should be able to produce
a read-only explanation of what it would do and why.

## Minimum viable Agent Lease

The smallest Agent Lease is scoped execution authority for one Project Run.

Minimum lease fields:

```text
lease_id
run_id
agent_identity_id
issued_by_identity_id
authority_basis
granted_actions
granted_capabilities
issued_at
expires_at
status
```

Minimum states:

```text
drafted
active
expired
revoked
completed
```

Read-only first version:

```text
scheduler candidate -> lease draft
```

A lease draft should answer:

```text
which agent would execute?
which run would it attach to?
which actions would it be allowed to perform?
which capabilities would it need?
who or what could issue it?
what authority basis applies?
```

A real active lease must remain impossible until:

```text
validator PASS
run state is runnable
identity exists
authority exists
capabilities are granted
lease scope is explicit
expiry is defined
```

## Smallest legal execution loop

The smallest legal runtime loop is:

```text
1. Event Record exists.
2. Causality is traceable.
3. /project validate returns PASS.
4. Event Queue marks or projects runnable work.
5. Scheduler selects an eligible Project Run.
6. Lease draft identifies agent, authority, actions, and capabilities.
7. Lease is issued only if authority and grants exist.
8. Agent executes one bounded step.
9. Agent records Event Record and/or checkpoint.
10. Validator runs again.
11. Run sleeps, blocks, waits, completes, or remains ready according to state law.
```

If validation fails at any point:

```text
stop
surface violation
cite precedent if known
surface remedy if known
do not schedule
do not lease
do not execute
do not auto-repair
```

## Validator gates

Validator PASS is required before:

```text
queue claim
scheduler selection
lease issuance
run resume
run completion
state transition enforcement
```

Validator FAIL requires:

```text
surface violations
surface precedent citations
surface remedies
prevent runtime progression
```

A future runtime may still show invalid state to operators. It must not treat
invalid state as executable work.

## Read-only components to build first

These can be implemented before mutable runtime behavior:

```text
Event Queue projection
Scheduler candidate report
Lease draft report
Execution preflight report
Runtime blocked/remedy report
```

These reports should be boring and deterministic. They should answer what would
happen, not make it happen. Yes, it is less dramatic. That is the point.

## Components that must wait

These should remain impossible until read-only preflight is proven:

```text
mutable Event Queue
automatic Scheduler
active Agent Lease allocation
automatic run wake
automatic run resume
automatic state repair
multi-agent execution
```

The correct order is:

```text
read-only projection
read-only candidate selection
read-only lease draft
operator-visible preflight
then bounded mutation
```

## Minimal executable runtime contract

A runtime component may execute only if it can answer:

```text
Which Project Run?
Which Event Record triggered this?
What causality chain applies?
Did validator PASS?
What state transition is required?
Which identity acts?
Which authority permits it?
Which capability grant enables it?
What Event Record will prove the result?
```

If any answer is missing, the component should not execute. It should report the
missing answer as a blocked preflight condition.

## Non-goals

This document does not implement:

```text
Event Queue
Scheduler
Agent Lease allocation
Wake Policy
execution worker
approval queue
automatic enforcement
automatic repair
```

It defines the runtime contract so future execution can only do legal things.
