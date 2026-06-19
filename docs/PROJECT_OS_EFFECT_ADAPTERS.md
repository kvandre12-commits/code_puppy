# Project OS Effect Adapters

Effect adapters are not separate runtimes. They are replaceable effect-plane
modules plugged into the same Project OS control plane.

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
