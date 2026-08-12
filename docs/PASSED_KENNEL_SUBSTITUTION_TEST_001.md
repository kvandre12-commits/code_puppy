# Passed Kennel Substitution Test 001

**Status:** proxy pass
**Protocol:** `docs/ANDROID_KENNEL_OPERATOR_SUBSTITUTION_TEST.md`
**Evidence source:** fresh-operator proxy via `planning-agent`

## Provenance

- **Target:** Android failure-triage knowledge, not software installability
- **Environment:** repo docs + failure log + kennel/tooling access as available to the proxy operator
- **Operator:** `planning-agent` acting as a fresh operator proxy
- **Install surface:** n/a for this test
- **Contamination state:** proxy run, not external human operator validation
- **Primary failure log used:** `outputs/mike_test_run_002_fresh_home_20260624-102434.log`

## Prompt used

The proxy operator was instructed to use only:
- repo docs
- kennel knowledge if available through tooling
- the failure log

and to recover only:
- failure summary
- relevant evidence
- known dead ends
- current leading explanation
- current challenger
- next discriminator
- recommended next step

## Result

The proxy operator successfully recovered:

- **Known dead ends**
  - `validation-requires-system-python`
  - `remove-playwright-and-android-is-fixed`
  - `browser-automation-never-works-on-android`
- **Current leading explanation**
  - `avoid-unnecessary-native-build-pressure`
- **Current challenger**
  - `validation-prefers-lean-runtime-paths`
- **Next discriminator**
  - `large environment + prebuilt wheels only`
- **Recommended next step**
  - run the discriminator before adding more governance/doctrine

The proxy operator also correctly avoided reopening the wrong question:
- it did **not** regress to "does Android work at all?"
- it explicitly recognized runtime viability as already supported

## Why this passes

This satisfies the minimum pass criteria in `docs/ANDROID_KENNEL_OPERATOR_SUBSTITUTION_TEST.md`:

- at least one rejected explanation recovered
- current leader recovered
- current challenger recovered
- next discriminator recovered

It also partially satisfies the stronger pass condition by recognizing:
- runtime viability vs fresh-install viability are separate slices
- the bottleneck is evidence, not governance

## What this proves

The repo + kennel artifact set is now strong enough for a fresh-ish proxy operator to recover the current Android posture from evidence instead of oral history.

## What this does not prove

- that a truly fresh human operator under live pressure will perform equally well
- that every future Android failure log will be as recoverable as this one

## Recommended next move

- Preserve this as a **proxy pass** for knowledge portability.
- If stricter external validation is desired later, repeat the same protocol with a true external human operator and record whether the result stays passed.
