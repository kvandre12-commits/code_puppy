# Mike Test Run 003

**Status:** planned
**Purpose:** remove **global Termux package-state contamination** as the next clean slice

This run is narrower than the general Mike test.
It is not trying to prove everything at once.

It is trying to answer one question:

> Can the upstream-main Android install path survive without preexisting Termux package state?

---

## Target

- **Target class:** upstream main
- **Repo URL:** `https://github.com/mpfaffenberger/code_puppy.git`
- **Install surface:** published-package Android flow
- **Evidence source:** clean run if possible
- **Contamination focus:** global Termux package state

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
- no preinstalled `uv`, `ripgrep`, or `proot` beyond what this run installs
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
env | grep '^VIRTUAL_ENV=' || true
pkg list-installed | grep -E '^(git|python|uv|ripgrep|proot)/' || true
```

### Contamination rule for Slice 2

If the baseline already shows any of these as preinstalled before the run:

- `uv`
- `ripgrep`
- `proot`
- `code-puppy`

mark the run **contaminated**.

`python` and `git` may appear only if they are part of the truly fresh Termux baseline or were just installed as part of the first documented setup step. Record exactly what you observed.

A same-phone app-data reset is not the target evidence standard for this slice anymore. Use a separate Android phone.

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
- save the result as `docs/FAILED_MIKE_TEST_003.md`

## If contamination appears

- stop immediately
- record the contamination source
- save the result as `docs/CONTAMINATED_MIKE_TEST_003.md`

## If it reaches a working agent cleanly

- save the result as `docs/PASSED_MIKE_TEST_003.md`

---

## What this slice should teach us

### If it passes

The remaining major Mike uncertainty shrinks toward:
- fresh external operator behavior

### If it fails cleanly

The failure becomes the next artifact.

### If it contaminates again

The contamination source becomes the next hidden dependency to isolate.
