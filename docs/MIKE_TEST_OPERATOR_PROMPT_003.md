# Mike Test Operator Prompt 003

Copy and paste this to the operator performing Mike Test Run 003.

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
- removing **global Termux package-state contamination**

Use only:
- a **separate Android phone**
- with a **fresh Termux install**
- with **no restored backups**

Required checklist before install:
- fresh Android device
- fresh Termux install
- no restored backups
- no existing `code-puppy`
- no existing `uv`
- no existing `ripgrep`
- no existing `proot`

Before install, capture this baseline:

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

If baseline already shows any of these already present:
- `uv`
- `ripgrep`
- `proot`
- `code-puppy`

stop and mark the run **contaminated**.

Then run these commands in order:

Note:
- If Termux prints `WARNING: apt does not have a stable CLI interface. Use with caution in scripts.`, that warning alone is **not** a failure.
- Treat it as failure only if the command itself actually fails.

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

Only if `pkg install uv` fails, use this fallback:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uvx --from code-puppy code-puppy-bootstrap detect --json
```

When done, save exactly one result:
- `docs/PASSED_MIKE_TEST_003.md`
- `docs/FAILED_MIKE_TEST_003.md`
- `docs/CONTAMINATED_MIKE_TEST_003.md`
