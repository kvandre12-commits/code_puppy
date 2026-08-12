# Android Mike Test Provenance

This note explains where the Mike test came from and what target it should be
used against.

It exists so the test does not drift into folklore or become disconnected from
the GitHub proof runs that motivated it.

---

## Why this test exists

The Mike test was not invented in a vacuum.
It was distilled from real Android/Termux install and proof work around the
GitHub Android installability effort, especially the PR496 proof trail.

That earlier work already established two important things:

1. **Runtime viability** is supported.
2. **Fresh-install portability** is the higher-leverage open question.

The Mike test is the acceptance-style version of that second question.

---

## Key GitHub proof lineage

These artifacts are the main ancestor evidence for the Mike-test shape:

- `outputs/pr496-body.md`
  - summary of the Android/Termux installability work and strongest proof claims
- `outputs/pr496-upstream-pr-ref-20260622-103342.log`
  - strongest fresh upstream clone + upstream PR-ref proof from the earlier run set
- `outputs/pr496-fresh-checkout-20260622-102330.log`
  - plain `uv sync` dev-path failure proving that not all install/validation paths are equal
- `outputs/pr496-squashed-bare-termux-proof.log`
  - earlier bare-Termux sandbox proof cited in the PR496 summary
- `outputs/pr496-after-upstream-pr-ref-proof.json`
  - PR-body state after the strongest upstream PR-ref proof was incorporated
- `outputs/pr496-after-current-proof.json`
  - PR-body state after current-branch proof wording was incorporated

These are the GitHub-run receipts that got ported into repo docs, kennel memory,
and the Android candidate/acceptance artifacts.

---

## What got ported into repo/kennel memory

The GitHub proof lineage was converted into local decision-support artifacts:

- `docs/ANDROID_ACCEPTANCE_SCORECARD.md`
- `docs/ANDROID_CANDIDATE_DECISIONS.md`
- `docs/ANDROID_HEAD_TO_HEAD_MECHANISMS.md`
- `docs/ANDROID_KENNEL_OPERATOR_SUBSTITUTION_TEST.md`
- `docs/MIKE_TEST_RUN_001.md`
- `docs/CONTAMINATED_MIKE_TEST_001.md`

And corresponding kennel captures preserve:

- supported viability
- rejected dead ends
- leading explanation vs challenger
- next discriminator
- Mike-test contamination rules

---

## Target under test

The Mike test must always declare its target explicitly.

Possible targets:

1. **Upstream main**
   - tests the current product baseline
2. **Upstream PR ref**
   - tests a specific upstream candidate fix
3. **Current fork PR branch**
   - tests our current proposed branch before or during PR work

### Current local context at time of writing

- local working branch: `droidpuppy`
- upstream remote: `origin -> https://github.com/mpfaffenberger/code_puppy.git`
- fork remote: `fork -> https://github.com/kvandre12-commits/code_puppy.git`

That means a Mike-style run can now be used in two very different ways:

- **acceptance against upstream main**
- **acceptance against our current PR branch/work branch**

Both are useful, but they answer different questions.

---

## Recommended interpretation

### If testing upstream main

Question:
- Can a fresh Android device install the current upstream product?

Typical install surface:
- published-package Android flow (`uvx --from code-puppy ...`, `uv tool install --refresh code-puppy`)

### If testing the current PR branch

Question:
- Does our proposed Android installability work actually improve the acceptance path?

Typical install surface:
- source-checkout runtime path from the branch under test
- prior PR496 proof used a fresh checkout plus local-source install/runtime validation rather than the published package path

This second use is especially valuable because it ties the Mike test directly to
current branch work instead of leaving it as a vague future acceptance ritual.

---

## Install-surface rule

If the target is a PR branch or upstream PR ref, do **not** pretend the published
PyPI/package flow is exercising the branch code.

Use a source-checkout validation path that actually installs/runs the checked-out
code under test.

The repo now includes `scripts/install_termux_checkout.sh` for this purpose on
Android/Termux, so branch/ref validation does not have to masquerade as a
published-package install.

The PR496 proof lineage demonstrates this explicitly:

- fresh checkout
- checkout PR ref
- local-source install/runtime validation on Android/Termux

Without that distinction, a supposed PR-branch Mike test may really just be a
published-package test wearing a fake mustache.

This is a form of **target contamination**:

- claim: testing PR branch
- reality: testing published package

---

## Acceptance provenance rule

Every acceptance-style artifact should record, at minimum:

- **Target**
- **Install surface**
- **Evidence source**
- **Contamination state**

Without that quartet, evidence becomes folklore fast.

A stronger pre-interpretation checklist is:

- **Target**
- **Environment**
- **Operator**
- **Install surface**
- **Contamination state**

Because a surprising amount of engineering folklore comes from one of those
being left implicit.

## Rule

A Mike-test artifact is incomplete unless it records:

- target repo URL
- target remote/ref/branch
- commit SHA under test
- whether the target was upstream main, upstream PR ref, or current fork PR branch
- install surface used (`published-package` vs `source-checkout`)
- evidence source (clean run / proxy run / imported historical proof / etc.)
- contamination state (clean / contaminated / unknown)

Without that, the result is too mushy to compare across runs.
