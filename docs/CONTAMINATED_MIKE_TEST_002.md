# Contaminated Mike Test 002

**Status:** contaminated
**Source run sheet:** `docs/MIKE_TEST_RUN_001.md`
**Operator prompt:** `docs/MIKE_TEST_OPERATOR_PROMPT_001.md`
**Log:** `outputs/mike_test_run_002_fresh_home_20260624-102434.log`

## Provenance

- **Target:** upstream main
- **Repo URL:** `https://github.com/mpfaffenberger/code_puppy.git`
- **Remote name:** upstream clone target
- **Branch/ref:** `main`
- **Commit SHA:** `1f34c4c60dc7e520a1e8483b9080eec867844d35`
- **Install surface:** published-package Android flow
- **Evidence source:** proxy run
- **Contamination state:** contaminated

## Why this is contaminated

This run used a **fresh HOME** and **clean environment variables**, but it did not use a fresh Termux base.
The run discovered preinstalled Termux package state before install:

- `git`
- `python`
- `uv`
- `ripgrep`
- `proot`

That means the run is not a clean external acceptance result.

## What was clean about it

The proxy run still removed several prior hidden states:

- `command -v code-puppy` was empty before install in the fresh HOME
- `VIRTUAL_ENV` was not set in the run environment
- a fresh upstream clone of `main` was created and the target SHA was recorded

## First meaningful failure

- **Failure step:** documented first maintenance step
- **Exact command:** `pkg update -y && pkg upgrade -y`
- **Observed result:** the run spent several minutes upgrading the lived-in Termux base and never reached the product install steps before the orchestration shell timed out
- **Full log path:** `outputs/mike_test_run_002_fresh_home_20260624-102434.log`

## Hidden dependency exposed

- **Category:** Environment assumption

### Explanation

The documented Android flow assumes the package-manager maintenance step is a routine prelude.
On a lived-in Termux environment, that step can dominate the entire run and prevent the test from even reaching the Code Puppy install boundary.
This means non-fresh-device evidence can fail before product-specific evidence appears.

## What was learned

- upstream target provenance was captured cleanly (`main` at `1f34c4c60dc7e520a1e8483b9080eec867844d35`)
- fresh HOME removed prior `code-puppy` install contamination
- fresh HOME removed active virtualenv contamination
- the remaining contamination is now more localized: **global Termux package state**, not prior Code Puppy user-home state

## What was not learned

- whether the full documented upstream install path reaches a working agent from a truly fresh Termux base
- whether `uvx`, planner, tool install, and `code-puppy -i` all succeed in a clean external run

## Best interpretation

This is stronger than the first contaminated proxy run because it removed prior `code-puppy` and `VIRTUAL_ENV` leakage.
It is still **not** a clean Mike acceptance result.

## Recommended next move

- For true acceptance: run the operator prompt on a genuinely fresh device/Termux install.
- For further proxy work on this device: skip inventing new doctrine; use the existing evidence and move to external validation.
