# Project OS Institutions

This document defines the powers and prohibitions of major Project OS runtime
institutions.

Constitutional invariants live in `PROJECT_OS_CONSTITUTION.md`. Procedure lives
in `PROJECT_OS_EXECUTION_LOOP.md`.

## Runtime chain

```text
Validator
  -> Runnable Candidate Projection
      -> Selection Policy
          -> Scheduler
              -> Lease Authority
                  -> Execution
```

Each institution receives constrained authority from upstream. None may
manufacture downstream authority by itself.

## Validator

Question:

```text
Is this specific state legal?
```

May:

```text
inspect Project Run and Event state
apply state-machine law
cite precedent
surface remedies
return PASS or FAIL
```

Must not:

```text
mutate state
repair state
schedule work
issue leases
execute work
```

Failure effect:

```text
Validator FAIL prevents projection, selection, scheduling, lease issuance, and execution.
```

## Runnable Candidate Projection

Question:

```text
What may proceed?
```

May:

```text
consume validator output
publish runnable candidates
exclude invalid, blocked, waiting_approval, terminal, or otherwise ineligible runs
surface exclusion reasons, precedent, and remedy
```

Must not:

```text
mutate state
rank candidates
select candidates
wake runs
claim queue work
issue leases
execute work
```

First implemented command:

```text
/project run candidates
```

This is the formal docket. It answers:

```text
Show me every run that is legally eligible to proceed, without actually proceeding.
```

## Selection Policy

Question:

```text
Which eligible thing should go first?
```

May:

```text
consume runnable candidates
rank eligible candidates
select candidate(s)
explain policy inputs
```

First implemented command:

```text
/project run selection
```

This is the read-only agenda report. It consumes `/project run candidates` output
and selects one eligible candidate without dispatching, leasing, waking, or
executing anything.

Possible inputs:

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

Must not:

```text
create candidates
promote excluded runs
make invalid runs eligible
turn validator FAIL into runnable work
bypass waiting_approval
bypass blocked evidence
allocate leases
wake runs
dispatch work
```

Doctrine test case:

```text
Input:
  run-high    eligible, high priority
  run-low     eligible, low priority
  run-blocked blocked, high priority

Projection:
  Candidates: run-high, run-low
  Excluded  : run-blocked

Selection Policy:
  Selected: run-high
```

If `run-blocked` becomes selected, doctrine was violated.

## Scheduler

Question:

```text
How is the selected thing dispatched?
```

May:

```text
consume selected candidate(s)
prepare dispatch plan
identify required lease draft
identify proof event type
```

First implemented command:

```text
/project run dispatch-plan
```

This is the read-only dispatch evidence report. It consumes `/project run
selection` output and describes the dispatch action, required lease scope, and
proof event without dispatching, leasing, waking, or executing anything.

Must not:

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

The smallest scheduler is a dispatcher, not a judge and not a prioritizer.

## Lease Authority

Question:

```text
Who may perform which scoped action?
```

Boundary:

```text
Selected Run
  -> Dispatch Plan
      -> Lease Draft
          -> Authority Check
              -> Issued Lease
                  -> Execution
```

May:

```text
inspect identity and authority basis
inspect requested action/capability scope
issue scoped lease when checks pass
expire or revoke leases
```

First implemented command:

```text
/project run lease-draft
```

This is the read-only authority request report. It consumes `/project run
dispatch-plan` output and describes requested agent identity, action scope,
capability scope, authority check, and expiry without authorizing, issuing,
leasing, waking, or executing anything.

Second implemented command:

```text
/project run authority-check
```

This is the read-only authority check report. It consumes `/project run
lease-draft` output and reports whether identity, authority grant, and capability
grant evidence exists, and whether a lease is issuable, without authorizing,
issuing, leasing, waking, or executing anything.

Must not:

```text
make invalid runs executable
make excluded runs executable
select runs
rank candidates
bypass authority checks
expand lease scope after issue
execute without an issued lease
```

A lease draft describes requested authority. An issued lease records granted
authority.

## Execution

Question:

```text
What actually happens?
```

May:

```text
consume issued lease
perform one bounded authorized action
record Event Record and/or checkpoint
stop on missing authority
```

Must not:

```text
create authority
expand scope
continue without lease
repair-and-resume blocked work by itself
ignore validator failure
hide effects without Event Records
```

Execution should be obedient, not creative:

```text
Lease present? execute bounded action.
Lease absent? stop.
Blocked? emit evidence and stop.
Validator fail? stop.
Need more scope? request authority and stop.
```

## Read-only-first requirement

These institutions should appear as reports before they become mutating services:

```text
Runnable Candidate Projection
Selection Policy report
Scheduler dispatch plan
Lease draft report
Execution preflight report
Runtime blocked/remedy report
```
