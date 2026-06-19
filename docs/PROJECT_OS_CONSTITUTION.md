# Project OS Constitution

This document records Project OS system-wide invariants. These are slow-changing
rules that constrain every runtime component.

Procedure lives in `PROJECT_OS_EXECUTION_LOOP.md`. Institutional powers live in
`PROJECT_OS_INSTITUTIONS.md`.

## Governing principle

```text
The closer a component is to execution, the less authority it should possess.
```

Judgment belongs upstream. Effects happen downstream.

That principle explains the runtime shape:

```text
Legality -> Eligibility -> Priority -> Dispatch -> Authority -> Execution
```

## Separation of runtime powers

Project OS must not collapse these questions:

| Layer | Question |
|---|---|
| State | What exists? |
| Law | What is permitted? |
| Validation | Is this specific state legal? |
| Eligibility | What may proceed? |
| Priority | Which eligible thing should go first? |
| Selection | Which eligible thing was chosen? |
| Scheduling | How is the selected thing dispatched? |
| Authority | Who may perform which scoped action? |
| Execution | What actually happens? |

Invariant:

```text
State ≠ Legality ≠ Eligibility ≠ Priority ≠ Selection ≠ Scheduling ≠ Authority ≠ Execution
```

## Authority flow

Meta-doctrine:

```text
Authority may flow downstream.
Authority may not be created downstream.
```

Allowed authority flow:

```text
Validator may deny legality.
Runnable Candidate Projection may exclude candidates.
Selection Policy may rank candidates.
Scheduler may dispatch selected candidates.
Lease Authority may grant scoped execution rights.
Execution may perform bounded effects.
```

Forbidden authority creation:

```text
Selection Policy may not create eligibility.
Scheduler may not create eligibility or priority.
Lease may not create legality.
Execution may not create authority.
Execution may not repair-and-resume blocked work by itself.
Execution may not continue when lease, authority, or validation is missing.
```

## Eligibility and priority

```text
Eligibility ≠ Priority
Eligibility is upstream of Priority.
Priority cannot modify Eligibility.
```

Eligibility is permission. Priority is preference.

A high-priority excluded run is still excluded. Priority cannot launder bad work
into good work. Yes, apparently civilization requires writing that down.

## Dispatch and permission

```text
Dispatch is not permission.
Selected Run ≠ Authorized Agent Execution.
Scheduler dispatch intent ≠ issued lease.
Lease draft ≠ authority grant.
```

Dispatch may request authority. Dispatch may not mint authority.

## Validator supremacy

```text
Validator PASS is the runtime gate.
Validator FAIL stops runtime progression.
Validator > Projection > Selection Policy > Scheduler > Execution.
```

A future scheduler must not inspect raw Project Runs to decide legality. A future
selection policy must not inspect excluded runs to decide priority.

## Anti-blob doctrine

Every component answers one question. The moment one component answers two
questions, architectural drift begins.

Doctrine violations include:

```text
scheduler decides legality
scheduler ranks candidates
selection policy creates candidates
lease creates legality
execution creates authority
execution repairs and resumes blocked work
```

Valid behavior includes:

```text
validator denies illegal state
projection excludes ineligible runs
selection policy ranks existing candidates
scheduler dispatches selected candidate
lease grants scoped authority after checks
execution performs bounded authorized action
```

## Constitutional analogy

```text
Validator                     = Judicial branch
Runnable Candidate Projection = Court docket
Selection Policy              = Agenda setting
Scheduler                     = Clerk / dispatcher
Lease Authority               = Credential office
Execution                     = Executive action
```

Each layer receives authority from the layer above it. None may manufacture
authority on its own.
