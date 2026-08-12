# Mike Test Operator Prompt 005

Copy and paste this to the operator performing Mike Test Run 005.

---

Run this test exactly as written.

Rules:
- Do **not** ask Kurtis for help.
- Do **not** use aliases, helper scripts, or undocumented fixes.
- If anything fails, **stop immediately**.
- Copy the **exact failed command**.
- Copy the **exact error output**.
- If hidden setup is discovered, mark the run **contaminated**.

This slice is focused on one thing only:
- verifying that the **corrected published package artifact** installs cleanly on Android/Termux

Use only:
- a **separate Android phone**
- with a **fresh Termux install**
- with **no restored backups**

Before running anything below:
- replace `<CORRECTED_PUBLISHED_VERSION>` with the exact published version being tested
- if that corrected version is not yet published, stop and do not run this prompt
- if practical, also capture the published wheel SHA256 for that exact version and record it in the result artifact

Required checklist before install:
- fresh Android device
- fresh Termux install
- no restored backups
- no existing `code-puppy`
- no existing `uv`
- no existing `ripgrep`
- no existing `proot`
- no existing `rust`
- no existing `clang`

Before install, capture this baseline:

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

If baseline already shows any of these already present:
- `uv`
- `ripgrep`
- `proot`
- `rust`
- `clang`
- `code-puppy`

stop and mark the run **contaminated**.

Optional provenance capture before install:

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

Then run these commands in order:

Note:
- If Termux prints `WARNING: apt does not have a stable CLI interface. Use with caution in scripts.`, that warning alone is **not** a failure.
- Treat it as failure only if the command itself actually fails.

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

Only if `pkg install uv` fails, use this fallback:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uvx --from "code-puppy==<CORRECTED_PUBLISHED_VERSION>" code-puppy-bootstrap detect --json
```

When done, save exactly one result:
- `docs/PASSED_MIKE_TEST_005.md`
- `docs/FAILED_MIKE_TEST_005.md`
- `docs/CONTAMINATED_MIKE_TEST_005.md`
