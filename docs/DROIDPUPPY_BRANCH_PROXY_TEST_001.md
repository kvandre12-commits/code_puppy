# DroidPuppy Branch Proxy Test 001

**Status:** proxy evidence collected
**Purpose:** reduce branch uncertainty, not Android acceptance closure
**Log:** `outputs/droidpuppy_branch_proxy_test_001_20260624-094055.log`

---

## Provenance

- **Target:** current local branch HEAD snapshot
- **Repo URL (local):** `/data/data/com.termux/files/home/code_puppy_backup_20260617`
- **Repo URL (fork):** `https://github.com/kvandre12-commits/code_puppy.git`
- **Remote name:** local clone of current repo
- **Branch:** `droidpuppy`
- **Target SHA:** `c4843c1aa92a4d1a22bb13d5f899018dbc5c3520`
- **Fork remote SHA:** `16b33892a4013d9668723b01bffd1867e342a541`
- **Install surface:** `source-checkout`
- **Evidence source:** proxy run
- **Contamination state:** environment-contaminated for clean acceptance; target-valid for local branch snapshot

---

## Contamination review

### Target

- Valid for the **local HEAD snapshot** of `droidpuppy`
- Not evidence about the stale pushed fork ref at `16b33892a4013d9668723b01bffd1867e342a541`

### Environment

- Not a fresh Android phone
- Not a fresh Termux install
- Host `python` still resolved to repo venv on the parent environment
- The run intentionally used Termux system Python (`/data/data/com.termux/files/usr/bin/python3.13`) for the source-checkout install path

### Operator

- No Kurtis intervention occurred
- Run executed by SharpEdge as an instrumented proxy test

### Install surface

- Correct for PR/branch validation: local source checkout was actually installed and run
- This was **not** a published-package validation pretending to test the branch

---

## What was tested

From a fresh clone of the current local branch snapshot:

1. create a fresh venv with Termux system Python
2. install the checked-out branch code from local source
3. run import/runtime/bootstrap checks against that installed branch code

---

## Result

The branch proxy test passed.

Observed successes:

- local source build/install succeeded
- `import code_puppy` succeeded
- browser import surface succeeded without requiring Playwright at base install time
- `code-puppy --help` succeeded
- `code-puppy-bootstrap detect --json` succeeded
- `code-puppy-bootstrap plan --profile auto` selected `android-termux-lean`
- `uv run --no-dev --python /data/data/com.termux/files/usr/bin/python3.13 code-puppy --help` succeeded

---

## Hidden dependencies exposed

1. **Target drift**
   - local `droidpuppy` HEAD and `fork/droidpuppy` are not the same SHA
   - any claim about "the PR branch" must say whether it means local HEAD or pushed remote branch

2. **Parent-environment bleed-through warning**
   - `uv run` emitted a `VIRTUAL_ENV` mismatch warning because the parent shell had an active repo venv
   - result still passed, but this is evidence that environment provenance matters even during source-checkout proxy runs

---

## What this does prove

- The current local `droidpuppy` branch snapshot behaves plausibly on Android/Termux when its code is actually exercised through a source-checkout runtime path.

## What this does not prove

- That Android clean-install acceptance is complete
- That a fresh operator on a fresh device can install Code Puppy without Kurtis
- That the stale pushed fork branch behaves the same as the local HEAD snapshot
- That uncommitted local working-tree modifications were exercised in this run

---

## Best interpretation

This is **valid branch evidence**.
It is **not** a clean Mike acceptance result.

That distinction is the whole point.

---

## Recommended next move

If branch-level uncertainty matters next:

- push/synchronize the intended PR branch target
- rerun the same source-checkout proxy flow against the pushed ref

If acceptance-level uncertainty matters next:

- run the strict clean Mike test
- do not rescue it
- capture either `PASSED_MIKE_TEST_001.md` or `FAILED_MIKE_TEST_001.md`
