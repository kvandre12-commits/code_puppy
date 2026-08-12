# Mike Test Run 004

**Status:** planned
**Purpose:** test whether the published-package Android failure is specifically caused by missing native build tooling (`rust` + `clang`)

This run is narrower than a general Android acceptance claim.
It is a direct follow-up to Mike Test 003.

It is trying to answer one question:

> Can the upstream-main published-package Android install path survive on a separate fresh phone when `rust` and `clang` are installed explicitly as part of the documented run?

---

## Why this slice exists

Mike Test 003 failed cleanly at:

- `uv tool install --refresh code-puppy`

with operator-reported clues including:

- failed to build `cryptography`
- failed to build `maturin`
- `Rust not found`
- Android CPython 3.13 aarch64 target

The current lean planner still auto-selects `android-termux-lean`, which currently recommends only:

- `ripgrep`
- `proot`

That means the next honest discriminator is to keep the same clean published-package path, but explicitly add the native build toolchain as the new mutant.

---

## Target

- **Target class:** upstream main
- **Repo URL:** `https://github.com/mpfaffenberger/code_puppy.git`
- **Install surface:** published-package Android flow
- **Evidence source:** clean run if possible
- **Contamination focus:** preexisting package state, especially native build tools

---

## Required environment for this slice

Use this only:

1. **Separate Android phone**
2. **Fresh Termux install** on that phone
3. **No restored backups**

If any of those are false, stop and mark the run contaminated before install begins.

---

## Clean win condition

All of the following must be true:

- fresh Android device for this test
- fresh Termux install
- no restored backups
- no existing `code-puppy`
- no active virtualenv
- no preinstalled `uv`, `ripgrep`, `proot`, `rust`, or `clang` beyond what this run installs
- commands executed exactly from the operator prompt
- no Kurtis rescue

---

## Clean-state capture before install

Run these first and paste the output exactly:

```bash
uname -a
getprop ro.build.version.release
termux-info || true
command -v code-puppy || true
command -v uv || true
command -v python || true
command -v rustc || true
command -v clang || true
env | grep '^VIRTUAL_ENV=' || true
pkg list-installed | grep -E '^(git|python|uv|ripgrep|proot|rust|clang)/' || true
```

### Contamination rule for Slice 4

If the baseline already shows any of these as preinstalled before the run:

- `uv`
- `ripgrep`
- `proot`
- `rust`
- `clang`
- `code-puppy`

mark the run **contaminated**.

`python` and `git` may appear only if they are part of the truly fresh Termux baseline or were just installed as part of the first documented setup step. Record exactly what you observed.

Use a separate Android phone. Same-phone app-data reset is not the target evidence standard.

---

## Exact command sequence

Run these commands in order and copy them exactly into the run log:

Note:
- Termux may print `WARNING: apt does not have a stable CLI interface. Use with caution in scripts.` during `pkg` operations.
- That warning alone is not a test failure.
- Only treat it as failure if the command itself fails or exits unsuccessfully.

```bash
pkg update && pkg upgrade
pkg install python git
pkg install uv
pkg install rust clang
uvx --from code-puppy code-puppy-bootstrap detect --json
uvx --from code-puppy code-puppy-bootstrap plan --profile auto
pkg install ripgrep proot
uv tool install --refresh code-puppy
code-puppy -i
```

### Allowed fallback

Only if `pkg install uv` fails:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uvx --from code-puppy code-puppy-bootstrap detect --json
```

---

## If anything fails

- stop immediately
- do not fix it
- copy the exact command
- copy the exact error
- save the result as `docs/FAILED_MIKE_TEST_004.md`

## If contamination appears

- stop immediately
- record the contamination source
- save the result as `docs/CONTAMINATED_MIKE_TEST_004.md`

## If it reaches a working agent cleanly

- save the result as `docs/PASSED_MIKE_TEST_004.md`

---

## What this slice should teach us

### If it passes

The leading mechanism gets much stronger:
- the published-package Android path needed explicit native build tooling

### If it fails cleanly

The next artifact should tell us whether:
- `rust` alone was not enough
- `clang` alone was not enough
- a different native library/toolchain gap still exists
- Android wheel/platform compatibility is still the real blocker

### If it contaminates again

The contamination source becomes the next hidden dependency to isolate.
