# Mike Test Run 005

**Status:** planned
**Purpose:** verify that a **corrected published artifact** now installs cleanly on Android/Termux without dragging optional-heavy dependencies into the base install

This run is the post-fix acceptance slice.
It should only be used **after** a corrected package has been published.

It is trying to answer one question:

> Can the corrected published `code-puppy` artifact install cleanly on a fresh Android/Termux environment without requiring accidental native-build rescue?

---

## Target

- **Target class:** corrected published artifact
- **Repo URL:** `https://github.com/mpfaffenberger/code_puppy.git`
- **Published package version under test:** `<CORRECTED_PUBLISHED_VERSION>`
- **Published wheel SHA256 under test:** capture if practical
- **Install surface:** published-package Android flow with exact version pin
- **Evidence source:** clean run if possible
- **Contamination focus:** preexisting package state, especially build-tool contamination

Replace `<CORRECTED_PUBLISHED_VERSION>` with the exact released version before running this test.
If that version is not yet published, this run is not ready.

If practical, also capture the exact wheel SHA256 for that published version.
A version string is good provenance; a wheel hash is stronger provenance because it identifies the exact artifact under test.

---

## Why this slice exists

Mike Test 003 and follow-on investigation showed that the published artifact under test could diverge from repository dependency intent.
Older published package lineage pulled optional-heavy dependencies such as `tree-sitter-typescript` into the base install path.

This run is the acceptance check for the packaging fix.
It is not trying to repair the old run.
It is trying to validate the **new** published artifact.

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
- the exact published version under test is pinned in the install commands

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

### Contamination rule for Slice 5

If the baseline already shows any of these as preinstalled before the run:

- `uv`
- `ripgrep`
- `proot`
- `rust`
- `clang`
- `code-puppy`

mark the run **contaminated**.

`python` and `git` may appear only if they are part of the truly fresh Termux baseline or were just installed as part of the first documented setup step. Record exactly what you observed.

Use a separate Android phone. Same-phone app-data reset is weaker evidence and should not be mislabeled as a clean external run.

### Optional provenance strengthening

If practical, capture the exact published wheel SHA256 before install and save it in the result artifact.
This helper uses only stdlib Python and PyPI metadata:

```bash
python - <<'PY'
import json, urllib.request
version = "<CORRECTED_PUBLISHED_VERSION>"
url = f"https://pypi.org/pypi/code-puppy/{version}/json"
with urllib.request.urlopen(url, timeout=20) as r:
    data = json.load(r)
for file in data.get("urls", []):
    if file.get("filename", "").endswith(".whl"):
        print("filename:", file["filename"])
        print("sha256:", file["digests"].get("sha256", ""))
        break
PY
```

If this step is skipped, record version at minimum.

---

## Exact command sequence

Run these commands in order and copy them exactly into the run log.
Before running them, replace `<CORRECTED_PUBLISHED_VERSION>` everywhere with the actual published version.

Note:
- Termux may print `WARNING: apt does not have a stable CLI interface. Use with caution in scripts.` during `pkg` operations.
- That warning alone is not a test failure.
- Only treat it as failure if the command itself fails or exits unsuccessfully.

### Manual path under test

```bash
pkg update && pkg upgrade
pkg install python git
pkg install uv
uvx --from "code-puppy==<CORRECTED_PUBLISHED_VERSION>" code-puppy-bootstrap detect --json
uvx --from "code-puppy==<CORRECTED_PUBLISHED_VERSION>" code-puppy-bootstrap plan --profile auto
pkg install ripgrep proot
uv tool install --refresh "code-puppy==<CORRECTED_PUBLISHED_VERSION>"
code-puppy -i
```

### Scripted equivalent

The repo also ships a dedicated Termux installer that follows the same flow,
adds verification, and supports exact version pins plus clean-run enforcement:

```bash
curl -fsSL https://raw.githubusercontent.com/mpfaffenberger/code_puppy/main/scripts/install_termux.sh | \
  bash -s -- --yes --version <CORRECTED_PUBLISHED_VERSION> --require-clean
```

### Allowed fallback

Only if `pkg install uv` fails:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uvx --from "code-puppy==<CORRECTED_PUBLISHED_VERSION>" code-puppy-bootstrap detect --json
```

---

## If anything fails

- stop immediately
- do not fix it
- copy the exact command
- copy the exact error
- save the result as `docs/FAILED_MIKE_TEST_005.md`

## If contamination appears

- stop immediately
- record the contamination source
- save the result as `docs/CONTAMINATED_MIKE_TEST_005.md`

## If it reaches a working agent cleanly

- save the result as `docs/PASSED_MIKE_TEST_005.md`

---

## What this slice should teach us

### If it passes

The packaging fix becomes much stronger:
- the corrected published artifact now matches lean dependency intent closely enough to survive a clean Android install path

### If it fails cleanly

The failure becomes the next artifact.
It should tell us whether:
- a different published dependency still leaked into base install
- the corrected artifact was not actually the one installed
- Android platform compatibility still has a remaining blocker unrelated to the previously exposed packaging drift

### If it contaminates again

The contamination source becomes the next hidden dependency to isolate.
