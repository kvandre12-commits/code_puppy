# Project OS Execution Loop

This document defines the smallest legal runtime procedure for executing a
Project Run.

Related doctrine:

```text
PROJECT_OS_CONSTITUTION.md   -> slow-changing invariants
PROJECT_OS_INSTITUTIONS.md   -> branch powers and prohibitions
PROJECT_OS_STATE_MACHINE.md  -> Project Run lifecycle law
PROJECT_OS_REMEDIES.md       -> lawful responses to violations
```

## Runtime stack

```text
Governance Stack:
Identity -> Authority -> Events -> Causality -> State Machine -> Validator -> Precedent -> Remedy

Runtime Stack:
Project -> Project Run -> Event Queue -> Runnable Candidate Projection -> Selection Policy -> Scheduler -> Agent Lease -> Execution
```

Execution is downstream of judgment. It must not invent legality, eligibility,
priority, or authority. The constitutional summary is:

```text
The closer a component is to execution, the less authority it should possess.
Authority may flow downstream.
Authority may not be created downstream.
```

## Minimum legal execution loop

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

## Gate order

The runtime gates are ordered:

```text
Legality
  -> Eligibility
      -> Priority
          -> Dispatch
              -> Lease Authority
                  -> Execution
```

Meaning:

```text
Validator blocks illegal work.
Runnable Candidate Projection blocks ineligible work.
Selection Policy orders eligible work only.
Scheduler dispatches selected work only.
Lease Authority grants scoped execution rights only.
Execution consumes issued authority only.
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

## Runnable Candidate Projection

The first implemented read-only runtime projection is:

```text
/project run candidates
```

It reads Project Runs and validator output, then reports:

```text
Candidates: legal and eligible runs
Excluded  : invalid, blocked, waiting_approval, terminal, or otherwise ineligible runs
```

It does not mutate state, claim queue work, allocate leases, wake runs, or
schedule execution. It is a docket, not a scheduler. Tiny gavel, no forklift.

## Selection and dispatch

Selection Policy consumes candidates. It does not create candidates.

```text
Eligibility is upstream of Priority.
Priority cannot modify Eligibility.
```

Scheduler consumes selected candidates. It does not rank candidates or decide
legality.

```text
Selected candidate -> dispatch plan
```

Dispatch is not permission:

```text
Selected Run ≠ Authorized Agent Execution
Scheduler dispatch intent ≠ issued lease
Lease draft ≠ authority grant
```

## Lease and execution

Lease boundary:

```text
Selected Run
  -> Dispatch Plan
      -> Lease Draft
          -> Authority Check
              -> Issued Lease
                  -> Execution
```

A real active lease requires:

```text
validator PASS
run state is runnable
selection exists
dispatch plan exists
identity exists
authority exists
capabilities are granted
lease scope is explicit
expiry is defined
```

Execution should be obedient, not creative:

```text
Lease present? execute bounded action.
Lease absent? stop.
Blocked? emit evidence and stop.
Validator fail? stop.
Need more scope? request authority and stop.
```

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

These reports should answer what would happen, not make it happen.

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

It defines procedure so future execution can only do legal things.
