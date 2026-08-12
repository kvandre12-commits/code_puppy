# Android Acceptance Scorecard

This scorecard tracks Android **platform maturity**, not just scattered observations.

It defines what "Android support" means in operational terms.

For detailed candidate posture and current explanations, defer to:

- `docs/ANDROID_CANDIDATE_DECISIONS.md`

For investigation and comparison support, see:

- `docs/ANDROID_HEAD_TO_HEAD_MECHANISMS.md`
- `docs/ANDROID_KENNEL_OPERATOR_SUBSTITUTION_TEST.md`
- `docs/ANDROID_VALIDATION_MUTANT_MATRIX.md`

---

## Android Support Acceptance Threshold

A stronger claim of Android support requires progress across **four independent tests**:

1. **Runtime viability passes**
2. **Fresh-install viability passes**
3. **Mike installer test passes**
4. **Kennel operator-substitution test passes**

These are intentionally separate.
A project can pass one and fail another.

---

## Current scorecard

| Test | Question | Current status | Why it matters | Next move |
|---|---|---|---|---|
| Runtime Viability | Can Code Puppy run on Android? | Supported | Proves the system can operate on Android at all | Preserve, don’t reopen existentially without contradictory evidence |
| Fresh-Install Viability | Can upstream Code Puppy become operational on Android through a documented path? | Active platform-port effort | Helps the next user, not just the current operator | Run the current discriminator: `large environment + prebuilt wheels only` |
| Mike Installer Test | Can a fresh Android device starting from the declared target ref reach a working installation without Kurtis-specific setup knowledge? | Proxy evidence strengthened; clean external run still pending | Tests whether the product stands on its own, and can also be aimed at our current PR branch to reduce uncertainty before final upstream acceptance | See `docs/ANDROID_MIKE_TEST_PROVENANCE.md`, `docs/CONTAMINATED_MIKE_TEST_001.md`, and `docs/CONTAMINATED_MIKE_TEST_002.md`; the latest fresh-HOME proxy removed prior `code-puppy`/`VIRTUAL_ENV` leakage but remained contaminated by lived-in Termux package state |
| Kennel Operator-Substitution Test | Can a fresh operator triage an Android failure from kennel + repo + logs without Kurtis oral history? | Proxy pass collected; external clean run still pending | Tests whether the knowledge stands on its own | See `docs/PASSED_KENNEL_SUBSTITUTION_TEST_001.md`; later, repeat with a true external human operator if stricter validation is needed |

---

## Why these tests are independent

- Passing **Runtime Viability** does **not** prove a fresh user can install the system.
- Passing **Fresh-Install Viability** does **not** prove a fresh operator can debug failure.
- Passing the **Mike test** does **not** prove the kennel can guide investigation.
- Passing the **kennel test** does **not** prove the install path itself is smooth.

That independence is useful because it prevents the lazy claim:

- "Android support exists" 

when the real answer may be:

- runtime works
- install path still rough
- operator substitution not yet proven

---

## Governance filter

Before adding:

- a new doctrine
- a new category
- a new controller
- a new ontology layer

ask:

> Does this improve one of the four Android acceptance tests?

If not, it is probably not the current bottleneck.

---

## Constitutional angle

These tests are not just Android tests.
They also test the broader Project OS / kennel philosophy:

- knowledge should outlive sessions
- decisions should outlive operators
- evidence should outlive conversations

### Mike test asks
- Can the **software** outlive the discoverer?

### Kennel test asks
- Can the **knowledge** outlive the discoverer?

---

## Current best summary

Android support is no longer one vague claim.
It is a measurable maturity stack.

Current posture:

- Runtime viability: **supported**
- Fresh-install viability: **active work**
- Mike installer test: **proxy evidence strengthened; clean external run pending**
- Kennel substitution test: **proxy pass collected; external clean run pending**

That means Android is already a viable execution environment, but full platform maturity still depends on proving operator-independent install and recovery.
