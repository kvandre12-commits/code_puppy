# Mike Test Operator Prompt 001

Copy and paste this to the operator performing the clean Mike test.

---

Run the clean Mike test exactly as written below.

Rules:
- Do **not** ask Kurtis for help.
- Do **not** use personal shortcuts, aliases, helper scripts, or undocumented fixes.
- If anything fails, **stop immediately**.
- Copy the **exact command** that failed.
- Copy the **exact error output**.
- Mark the run as either:
  - **failed**
  - or **contaminated** if Kurtis intervened or hidden setup leaked in.

Before running install commands, capture this clean-state output:

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

Then run these commands in order:

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

If `pkg install uv` fails, use only this fallback:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uvx --from code-puppy code-puppy-bootstrap detect --json
```

If you discover any of the following, stop and mark the run **contaminated**:
- Kurtis gave instructions beyond the written docs
- a helper script or alias was used
- `code-puppy` was already installed and reused
- a virtualenv was already active
- the target under test changed without being recorded

When done, save the result into one of these artifacts:
- `docs/PASSED_MIKE_TEST_001.md`
- `docs/FAILED_MIKE_TEST_001.md`
- `docs/CONTAMINATED_MIKE_TEST_001.md`
