# Project OS Execution Loop

The governance stack is now strong enough to constrain behavior.

```text
Governance Stack:
Identity -> Authority -> Events -> Causality -> State Machine -> Validator -> Precedent -> Remedy

Runtime Stack:
Project -> Project Run -> Event Queue -> Runnable Candidate Projection -> Selection Policy -> Scheduler -> Agent Lease -> Execution
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

## Runtime question boundaries

Project OS must keep these questions separate:

| Layer | Question |
|---|---|
| State | What exists? |
| Law | What is permitted? |
| Validation | Is this specific state legal? |
| Eligibility | What may proceed? |
| Priority | Which eligible thing should go first? |
| Selection | Which eligible thing was chosen? |
| Scheduling | How is the selected thing dispatched? |
| Execution | What actually happens? |

The invariant is:

```text
State ≠ Legality ≠ Eligibility ≠ Priority ≠ Selection ≠ Scheduling ≠ Execution
Eligibility ≠ Priority
Eligibility is upstream of Priority.
Priority cannot modify Eligibility.
```

This separation is the difference between a governed process engine and one big
scheduler wearing a fake mustache.

The scheduler must not inspect raw Project Runs to decide legality or priority.
It should consume the output of Selection Policy, which consumes the Runnable
Candidate Projection:

```text
Project Run
  -> Validator
      -> Runnable Candidate Projection
          -> Selection Policy
              -> Scheduler
                  -> Execution
```

That keeps governance drift and priority drift out of dispatch machinery. The
validator applies law but never performs work. The projection publishes eligible
runs but never selects or wakes them. Selection Policy chooses among eligible
runs but never decides legality or creates candidates. The scheduler dispatches
selected work but never ranks candidates or decides what is legal. Execution
performs bounded work only after the upstream layers allow it.

The first formal docket command is:

```text
/project run candidates
```

It answers:

```text
Show me every run that is legally eligible to proceed, without actually proceeding.
```

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

## Minimum viable Selection Policy

The smallest Selection Policy is a ranking decision over already eligible runs.
It is not validation, not projection, not dispatch, and not execution.

Read-only first version:

```text
Runnable Candidate Projection -> selected candidate report
```

It should answer:

```text
which eligible candidates were considered?
which candidate was selected?
why was it selected first?
which policy rule applied?
```

Possible policy inputs:

```text
explicit priority
FIFO order
aging
fairness
deadlines
quotas
resource limits
operator focus
```

Minimum selection fields:

```text
selected_run_id
candidate_run_ids
policy_name
selection_reason
policy_inputs
```

The Selection Policy consumes candidates. It does not create candidates.

The Selection Policy must not:

```text
make invalid runs eligible
turn validator FAIL into runnable work
bypass waiting_approval
bypass blocked evidence
promote excluded runs
create candidates from raw Project Runs
allocate leases
wake runs
dispatch work
```

Eligibility is permission. Priority is preference. Those are not the same thing,
because apparently civilization requires writing that down.

Constitutional analogy:

```text
Validator                 = Judicial branch
Runnable Candidate Projection = Court docket
Selection Policy          = Agenda setting
Scheduler                 = Clerk / dispatcher
Execution                 = Executive action
```

Each layer receives authority from the upstream layer. None may manufacture
authority on its own.

Doctrine test case:

```text
Input runs:
  run-high    eligible, high priority
  run-low     eligible, low priority
  run-blocked blocked, high priority

Runnable Candidate Projection:
  Candidates: run-high, run-low
  Excluded  : run-blocked

Selection Policy:
  Selected: run-high

Scheduler:
  Dispatch: run-high
```

If any layer can jump from `run-blocked` to `Selected`, the architecture has a
doctrine violation. Priority never turns an excluded run into an eligible run.

## Minimum viable Scheduler

The smallest Scheduler is a dispatcher, not a judge and not a prioritizer.

Read-only first version:

```text
Selected candidate -> dispatch plan
```

It should answer:

```text
which selected run would be dispatched?
which dispatch action would be attempted?
which lease draft would be required?
which Event Record would prove dispatch?
```

Minimum dispatch plan fields:

```text
run_id
selection_policy
selected_at
dispatch_action
required_lease_scope
proof_event_type
```

The scheduler must not:

```text
inspect raw Project Runs to decide eligibility
rank eligible candidates
wake archived runs
resume completed runs
bypass waiting_approval
bypass blocked evidence
allocate leases without authority
invent causality
invent remedies
```

Mutable scheduling can come later. First, the scheduler should be able to produce
a read-only dispatch plan from a selected candidate.

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
4. Runnable Candidate Projection publishes eligible work.
5. Selection Policy chooses among eligible candidates.
6. Scheduler prepares dispatch for the selected run.
7. Lease draft identifies agent, authority, actions, and capabilities.
8. Lease is issued only if authority and grants exist.
9. Agent executes one bounded step.
10. Agent records Event Record and/or checkpoint.
11. Validator runs again.
12. Run sleeps, blocks, waits, completes, or remains ready according to state law.
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
selection policy choice
scheduler dispatch
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
Runnable Candidate Projection (`/project run candidates`)
Event Queue projection
Selection Policy report
Scheduler dispatch plan
Lease draft report
Execution preflight report
Runtime blocked/remedy report
```

The first implemented read-only runtime projection is:

```text
/project run candidates
```

It reads Project Runs and validator output, then reports runnable candidates and
excluded runs. It does not mutate state, claim queue work, allocate leases, wake
runs, or schedule execution.

These reports should be boring and deterministic. They should answer what would
happen, not make it happen. Yes, it is less dramatic. That is the point.

## Components that must wait

These should remain impossible until read-only preflight is proven:

```text
mutable Event Queue
automatic Selection Policy
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
read-only selection policy
read-only dispatch plan
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
Selection Policy
Scheduler
Agent Lease allocation
Wake Policy
execution worker
approval queue
automatic enforcement
automatic repair
```

It defines the runtime contract so future execution can only do legal things.
