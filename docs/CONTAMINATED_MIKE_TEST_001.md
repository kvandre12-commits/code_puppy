# Contaminated Mike Test 001

**Status:** contaminated
**Source run sheet:** `docs/MIKE_TEST_RUN_001.md`
**Log:** `outputs/mike_test_run_001_proxy_20260624-060139.log`

## Target snapshot for this contaminated proxy run

- Target class: upstream main proxy run from fresh upstream clone
- Repo URL: `https://github.com/mpfaffenberger/code_puppy.git`
- Remote name: `origin`-style upstream target
- Branch/ref: `main`
- Commit SHA: `1f34c4c60dc7e520a1e8483b9080eec867844d35`
- Install surface: published-package Android flow
- Evidence source: proxy run executed locally from a fresh upstream clone on an already-prepared Android/Termux environment
- Contamination state: contaminated

## Why this is contaminated

This run did **not** satisfy the strict Mike-test rules.
It was a useful proxy run, but not a clean acceptance test.

Contamination sources:

- not a fresh Android phone
- not a fresh Termux install
- existing environment state was present
- `python` on PATH resolved to `/data/data/com.termux/files/home/code_puppy_backup_20260617/.venv/bin/python`
- `uv tool install --refresh code-puppy` reported:
  - `` `code-puppy` is already installed ``
- `ripgrep` and `proot` were already present

That means this run did **not** prove that a brand-new operator on a clean device
could complete the install from zero.

## What it *did* prove

The documented Android path from upstream main is operationally plausible on
this Android/Termux environment without mid-run rescue or ad hoc fixes.

Observed:

- fresh upstream clone from `https://github.com/mpfaffenberger/code_puppy.git`
- upstream commit: `1f34c4c60dc7e520a1e8483b9080eec867844d35`
- `uvx --from code-puppy code-puppy-bootstrap detect --json` succeeded
- `uvx --from code-puppy code-puppy-bootstrap plan --profile auto` succeeded
- profile selected: `android-termux-lean`
- `pkg install -y ripgrep proot` succeeded (already installed)
- `uv tool install --refresh code-puppy` succeeded in the weak sense that the tool was already installed
- `code-puppy --help` succeeded

## Relevant Android posture

- Runtime viability: supported
- Fresh-install viability: still active work
- Mike installer test: **not yet cleanly run**
- Current leader: `avoid-unnecessary-native-build-pressure`
- Current challenger: `validation-prefers-lean-runtime-paths`
- Current discriminator: `large environment + prebuilt wheels only`

## What hidden dependency remains untested

The most important remaining unknown is still the real zero-state install path.
This run did not remove Kurtis/setup dependency strongly enough to tell us:

- whether docs are sufficient from zero
- whether bootstrap/install succeeds when `code-puppy` is not already installed
- whether package/tool presence was silently inherited from prior setup
- whether a fresh operator would recover cleanly from first failure

## Recommended next slice

Run a **strict** Mike test with these conditions enforced:

- fresh device or meaningfully clean Android environment
- fresh Termux
- no preinstalled `code-puppy`
- no project venv shadowing `python`
- no Kurtis intervention

The next real acceptance artifact should be one of:

- `docs/PASSED_MIKE_TEST_001.md`
- `docs/FAILED_MIKE_TEST_001.md`

This contaminated run is useful evidence, but it is **not** the final boss receipt.
