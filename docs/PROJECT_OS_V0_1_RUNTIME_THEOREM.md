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

## Contract Validation posture

The next phase is not adapter development. It is contract validation.

```text
Do not protect the theorem.
Protect the experiment.
```

For each boundary, state the hypothesis, state what would falsify it, run the
smallest bounded effect, then interpret the result. Adapter bugs mean fix adapter
code. Contract failures mean rethink the platform rule.

Do not patch contradictions with special cases until the failure has been
classified. Otherwise the theorem becomes unfalsifiable folklore.

Documentation is experimental control. It is not just knowledge storage; it
pre-registers what evidence would change the architecture before the boundary
experiment runs. That prevents future commits from quietly rewriting a failure as
success.

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

| Boundary | Hypothesis | Contract failure may mean |
| --- | --- | --- |
| Browser | Authority -> Lease -> External Effect -> Audit | effect handling incomplete |
| Android | Authority -> Lease -> Device Effect -> Audit | lease/effect model incomplete |
| me@sams | Authority -> Lease -> Approved View -> Audit | identity/trust model incomplete |
| GitHub | Authority -> Lease -> Persistent Mutation -> Audit | effect lifecycle incomplete |
| Robinhood | Authority -> Lease -> Financial Effect -> Audit | governance model incomplete |

Robinhood is intentionally last: bug and governance failure can have materially
different consequences when money movement is involved. Treat any evidence that
financial actions need a different approval chain or state model as legitimate
data, not as an attack on the theorem.

## Contract Validation status

The theorem is accumulating evidence, not claiming final proof.

```text
No-op boundary    -> PASS
Browser boundary  -> PASS
Android boundary  -> PASS
```

Confidence ladder:

```text
Level 0  Idea                         -> Authority -> Lease -> Effect -> Audit
Level 1  Internal runtime             -> No-op PASS
Level 2  External runtime             -> Browser PASS, Android PASS
Level 3  Identity/application boundary -> me@sams PENDING
Level 4  Persistent mutation          -> GitHub PENDING
Level 5  Financial-risk boundary      -> Robinhood PENDING
```

Current confidence level:

```text
External effects can be governed without changing the governance core.
```

Active hypothesis:

```text
Project OS authority can cross an identity-bearing application boundary without
requiring capability translation.
```

## Next application-boundary test

The next boundary should be boring on purpose, but it should cross identity and
application trust:

```text
Authority
  -> Lease
      -> Approved me@sams View
          -> Audit
```

It should try to produce this diff shape:

```text
+ me_sams_execution.py
+ me_sams execution tests
0 Authority changes
0 Lease changes
0 Validator changes
0 Audit framework changes
```

Success means Project OS authority can govern access to an identity-bearing
application boundary without inventing a second permission system. A need for
special me@sams authority, special me@sams permissions, or a special validator
path is not an adapter bug by default; classify it as possible contract evidence.

A likely pressure point is capability translation:

```text
Project OS Authority
  -> external application identity/session/permission model
      -> approved bounded view
```

If that mapping is necessary, do not smuggle it in as a me@sams exception. Record
it as evidence that the theorem may need an explicit external capability mapping
concept.

Pre-registered outcomes:

```text
Outcome A: Authority -> Lease -> Approved me@sams View -> Audit
           works directly.
           Result: theorem gains credibility.

Outcome B: Authority -> Capability Translation -> me@sams identity/permissions
           -> Approved View -> Audit is necessary.
           Result: theorem expands; a missing concept was discovered.

Outcome C: special permission + special validator + special lease + special
           trust path appear only for me@sams.
           Result: experiment compromised; this is the folklore path.
```

Do not include task submission, workflow mutation, agent orchestration,
background recovery, or message sending in the first me@sams experiment. Those
belong after the approved-view boundary is understood.
