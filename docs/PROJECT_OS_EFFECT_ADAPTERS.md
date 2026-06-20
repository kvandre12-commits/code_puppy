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

Protect the experiment, not the theorem. Learn something true and do not hide
it. If a boundary requires special Authority, Lease, Validator, or Audit
behavior, classify that as possible contract evidence before adding exceptions.
Theorem changed is not the same as theorem failed.

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

If a boundary presents biometric/MFA/operator approval, do not treat that as an
adapter bug by default and do not bypass it. Pause at an explicit human approval
checkpoint, let the operator satisfy the external challenge, then continue only
inside the lease/scope and audit the bounded effect. If this pattern repeats
across adapters, record it as possible contract evidence instead of hiding it in
one adapter.

Keep effect execution separate from effect observation. If an effect launches but
ADB/UI/CDP inspection fails afterward, classify the observer failure separately.
Do not mark the effect failed unless execution itself failed; do not mark the
experiment proven unless runtime audit evidence exists.

Do not promote one-off pressure into a theorem concept. Capability Translation,
Human Approval Checkpoint, Effect Observation Boundary, Location / Proximity
Precondition, and Work-State / Duty-State Precondition are watch-list items until
multiple unrelated boundaries demand them.

Do not collapse every gate into authentication. Identity gates prove who is
acting; duty-state gates prove the context/state under which they are acting.
Adapters must not perform a state-changing action, such as employment clock-in,
merely to unlock broader downstream capabilities.

## Capability OS milestone ladder

Project OS has moved beyond a generic agent framework. It is becoming a governed
capability operating system for agents.

The next technical milestone should prove a staged capability ladder:

```text
AuthorityGrant
  -> Authority Registry Validation
      -> Lease Issue
          -> Execute No-op
              -> Execute Android Intent
                  -> Execute Browser Action
                      -> Execute Tool Call
```

Each stage should prove the same thing with a stronger effect:

```text
governance controls the effect
without skipping Authority
without skipping validation
without skipping Lease issue
without skipping Lease consumption
without skipping Audit
```

This is the Project OS equivalent of process permissions and capability security,
but for AI agents instead of human users. The lease is the revocable execution
permission. Lease consumption is the one-shot capability boundary. The audit
trail is the operating-system record of what happened.

The test is not whether an agent can do the thing. The test is whether the agent
can do the thing only through the governed path.

No effect may occur unless:

```text
1. Authority is registered.
2. Authority validates.
3. Lease is issued.
4. Lease is unexpired.
5. Lease is unconsumed.
6. Execution succeeds.
7. Audit event is recorded.
```

Different adapters may touch different systems, but they do not get different
governments. Android intents, browser actions, and tool calls are effect adapters
behind the same authority substrate.

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
