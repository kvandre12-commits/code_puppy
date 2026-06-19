# Project OS v0.1 Runtime Theorem Proven

Status: real, tested, not production-complete.

## Claim

```text
Authority -> Lease -> One bounded Effect -> Audit
```

Project OS v0.1 proves that a bounded effect can be governed by authority and a
one-shot lease, then recorded as audit evidence.

## Evidence

- No-op effect implemented and tested.
- Browser effect implemented and tested.
- Refusal paths verified for missing authority, wrong scope, expired lease,
  reused lease, revoked authority, and missing lease.
- First external effect contact exposed one hidden coupling: the audit catalog
  assumed fixed effect event types.
- Coupling was removed through a generic platform seam:

```text
<adapter>_effect_executed
```

- Browser adapter was added without browser-specific Authority, Lease,
  Validator, or Audit catalog exceptions.

## What changed after Browser

Before Browser, the claim was:

```text
Authority
  -> Lease
      -> One bounded Effect
          -> Audit
```

After Browser, the claim became:

```text
Authority
  -> Lease
      -> External Effect
          -> Audit
```

The theorem survived first contact with reality.

## Engineering loop

The sequence that matters is:

```text
Define theorem
  -> Implement theorem
      -> Document theorem
          -> Challenge theorem
              -> Find coupling
                  -> Generalize theorem
                      -> Retest theorem
```

New capabilities should continue to test the architecture instead of becoming
special-case governments.

## Boundary test ladder

The roadmap is not a list of adapters. It is a sequence of increasingly
difficult boundary tests:

```text
v0.1 Browser   -> external effect boundary
v0.2 Android   -> device boundary
v0.3 me@sams   -> application + identity + agent + workflow boundary
v0.4 GitHub    -> persistent mutation boundary
v0.5 Robinhood -> financial-risk boundary
```

Each step increases the consequence of a bad theorem. The goal is not to make the
agent do more things; it is to make the agent do bounded things through the same
contract without modifying the contract.

## Next repeatability test

One adapter can still be luck. The next adapter should be boring on purpose:

```text
launch approved activity once
consume lease
write android_effect_executed
refuse reuse
```

It should try to produce this diff shape:

```text
+ android_execution.py
+ android execution tests
0 Authority changes
0 Lease changes
0 Validator changes
0 Audit framework changes
```

If multiple adapters can plug in this way, the theorem starts becoming a platform
contract. Do not skip the boundary proof with complex workflows; otherwise it
becomes impossible to tell whether a failure came from the platform theorem or
from adapter complexity.
