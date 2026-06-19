# Project OS Effect Adapters

Effect adapters are not separate runtimes. They are replaceable effect-plane
modules plugged into the same Project OS control plane. The v0.1 milestone is
summarized in `PROJECT_OS_V0_1_RUNTIME_THEOREM.md`.

The system promise is:

```text
Authority -> Lease -> One bounded Effect -> Audit
```

The adapter promise is:

```text
noop_execution.py
browser_execution.py
android_execution.py
github_execution.py
robinhood_execution.py

all obey the same control plane.
```

## Baseline theorem

The no-op runtime proves the baseline theorem:

```text
valid AuthorityGrant
+ valid active unconsumed one-shot LeaseRecord
= exactly one bounded effect
+ consumed lease
+ audit EventRecord
```

For noop, the effect event is:

```text
noop_executed
```

Future adapters change the effect, not the theorem. Effect adapters use the
normalized audit event shape:

```text
<adapter>_effect_executed
```

For example, the browser adapter writes `browser_effect_executed` without adding
a browser-specific audit catalog rule.

## Browser adapter acceptance test

The first real browser adapter should not be judged by whether a browser opened.

It should be judged by whether the browser opened only because a valid lease
allowed exactly that one effect.

The target lifecycle is:

```text
AuthorityGrant
  -> authority-check
  -> LeaseRecord
  -> execute-browser
  -> lease consumed
  -> browser_effect_executed EventRecord
```

The positive case is:

```text
valid authority
+ valid one-shot lease for the exact browser action and URL scope
= one bounded browser effect
+ audit
```

The refusal table is sacred:

```text
missing authority  -> no lease
wrong confirm      -> no mutation
expired lease      -> no browser effect
reused lease       -> no second browser effect
revoked authority  -> no browser effect
wrong URL/scope    -> no browser effect
```

A browser adapter is therefore not special. It is the first external effect that
proves the control plane survives contact with the outside world.

## Boundary test ladder

Treat adapters as increasingly difficult boundary tests:

```text
Browser   -> external effect boundary
Android   -> device boundary
me@sams   -> application + identity + agent + workflow boundary
GitHub    -> persistent mutation boundary
Robinhood -> financial-risk boundary
```

The first effect for a new boundary should be boring: launch an approved screen,
read an approved view, retrieve an approved status, then consume the lease and
audit. Do not begin with complex workflows.

For me@sams specifically, the first experiment should cross the identity-bearing
application boundary without mutation:

```text
Authority -> Lease -> Approved me@sams View -> Audit
```

Do not begin with task submission, workflow mutation, agent orchestration,
background recovery, or message sending. If me@sams needs special authority or a
special trust path, treat that as possible contract evidence before patching.

If the approved-view test reveals a need to translate Project OS authority into
an external application permission/session model, record that as possible
capability-translation evidence. Do not hide it inside me@sams-only code.

Pre-register outcomes before implementing: direct pass means the theorem gains
credibility; capability translation means the theorem may need a new explicit
concept; me@sams-only special permissions, validators, leases, or trust paths
mean the experiment has been compromised.

Protect the experiment, not the theorem. If a boundary requires special
Authority, Lease, Validator, or Audit behavior, classify that as possible
contract evidence before adding exceptions.

Classify action type before implementing:

```text
approved view/read/status      -> read boundary
commit/comment/post/edit/send  -> persistent mutation boundary
financial/regulated action     -> high-risk boundary
```

For Reddit or LinkedIn style adapters, treat read-only approved views as the
first identity/reputation experiment. Posting, commenting, messaging,
endorsements, or profile edits are persistent public mutations and need their
own later mutation-boundary experiment.

## Adapter implementation rule

An adapter may:

```text
validate its effect-specific scope
perform one bounded external effect
consume the lease once
write one effect-specific audit event
```

An adapter must not:

```text
create authority
issue leases
repair missing grants
expand URL/action/capability scope
reuse consumed leases
hide external effects without EventRecords
```

If an adapter needs broader authority, it stops and requests authority. It does
not reinterpret the lease. Runtime obedience beats runtime creativity here.
