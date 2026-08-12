# Android Kennel Operator-Substitution Test

This is the harder Android/kennel test.

It does **not** ask:

- Can Kurtis solve the problem again?

It asks:

- Can a fresh operator use repo artifacts + kennel knowledge to triage a fresh Android install failure without oral history?

For canonical Android candidate posture, defer to:

- `docs/ANDROID_CANDIDATE_DECISIONS.md`

---

## Purpose

Measure whether the kennel has crossed from:

- memory store

into:

- knowledge-guided operations

A passing result means a new operator can move from:

- failure
- relevant evidence
- current explanations
- known dead ends
- next discriminator

without depending on Kurtis as the hidden runtime dependency.

---

## Test scenario

Set up an intentionally unfair environment:

- fresh Android phone
- fresh Termux
- fresh upstream checkout
- install attempt fails

Then hide or forbid:

- personal Android notes outside the repo/kennel
- oral-history explanation from Kurtis
- ad hoc memory shortcuts like “oh yeah, Playwright was the thing”

Allowed inputs:

- kennel
- repo docs
- failure log
- current checkout

---

## Questions the operator must answer

### 1. Do they find the known dead ends?

They should be able to discover at least:

- rejected: `validation-requires-system-python`
- rejected: `remove-playwright-and-android-is-fixed`
- rejected: `browser-automation-never-works-on-android`

### 2. Do they find the current leading explanation?

They should identify:

- leading candidate: `avoid-unnecessary-native-build-pressure`

### 3. Do they find the current challenger?

They should identify:

- active candidate: `validation-prefers-lean-runtime-paths`

### 4. Do they find the next discriminator?

They should identify:

- `large environment + prebuilt wheels only`

### 5. Do they avoid reopening the wrong question?

They should not regress to:

- “Can Code Puppy run on Android at all?”

They should recognize:

- Android runtime viability is already supported
- fresh-install viability is still active platform-port work

---

## Success criteria

### Minimum pass

A fresh operator can correctly recover:

- at least one rejected explanation
- the current leader
- the current challenger
- the next discriminator

### Strong pass

A fresh operator can also correctly articulate:

- runtime viability vs fresh-install viability are separate slices
- current bottleneck is evidence, not governance
- the Android stream is now a portability audit, not a dependency panic

### Failing patterns

The test fails if the operator primarily concludes:

- Playwright is the root cause
- system Python is required
- Android viability is still the main question
- more doctrine/governance should be added before running the discriminator

---

## Suggested operator workflow

1. Start with the failure log.
2. Query the kennel / read the canonical Android ledger.
3. Recover current status board posture.
4. Collect known false explanations first.
5. Identify current leading and competing explanations.
6. Identify the next discriminating mutant.
7. Stop theorizing and recommend the next evidence slice.

---

## Output template

A passing operator should be able to produce something like:

```text
Failure summary: ...
Relevant evidence: ...
Known dead ends: ...
Current leading explanation: avoid-unnecessary-native-build-pressure
Current challenger: validation-prefers-lean-runtime-paths
Next discriminator: large environment + prebuilt wheels only
Recommended next step: run the discriminator before adding governance.
```

---

## Why this matters

This is the knowledge equivalent of the fresh-install slice.

- Runtime viability helps the current operator.
- Fresh-install viability helps the next operator.
- Kennel-guided triage helps the next investigator.

If this test passes, the repo has demonstrated something stronger than memory:

- portable operational knowledge
