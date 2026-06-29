# Code Puppy on Android (Termux)

This is the canonical install flow for running Code Puppy on a phone with
Termux. It keeps the install **lean by default** and lets you attach optional
capabilities later, only if you actually want them.

## Mental model

- **Code Puppy** is the engine. It installs lean on Android via the bootstrap
  planner.
- **DroidPuppy** is an optional Android-native overlay. It is layered on *after*
  Code Puppy is installed.
- **Extras** (browser/image/fuzzy/search/provider) are opt-in, not mandatory.
  The phone install stays small by default.

If the goal is to **share or ship the Android story from main Code Puppy**,
start with [`ANDROID_MAIN_FIRST_SHARE.md`](ANDROID_MAIN_FIRST_SHARE.md). That
keeps the launch surface, proof path, and optional overlay attach in the right
order.

If the goal is specifically **build/handoff readiness** — meaning another human
should be able to run the correct Android validation lane without guessing — use
[`ANDROID_BUILD_HANDOFF.md`](ANDROID_BUILD_HANDOFF.md) for the exact commands,
pre-push checks, and handoff packet.

## Base install

### Step 0 — Get Termux properly

Install **Termux from F-Droid or GitHub**, not the Play Store version (that one
is stale).

### Step 1 — Recommended: run the Android onboarding command

This is the best fresh-user path. It owns the milestone-1 Android journey:
core Termux install, lean Code Puppy setup, optional DroidPuppy overlay attach,
`adb` detection/install, and a staged readiness summary.

```bash
curl -fsSL https://raw.githubusercontent.com/mpfaffenberger/code_puppy/main/scripts/onboard_android.sh | bash -s -- --yes
```

For Mike-style acceptance runs against an exact published artifact:

```bash
curl -fsSL https://raw.githubusercontent.com/mpfaffenberger/code_puppy/main/scripts/onboard_android.sh | \
  bash -s -- --yes --version 0.0.569
```

Useful flags:

- `--dry-run` — preview the exact commands
- `--skip-overlay` — keep it core-only for now
- `--skip-adb-install` — detect adb only, do not install `android-tools`
- `--skip-upgrade` — skip `pkg update && pkg upgrade`
- `--launch` — open `code-puppy -i` after the final summary

### Step 1b — Want only the lean core installer?

If you only want the engine install without the broader Android onboarding
journey, use the dedicated Termux installer directly:

```bash
curl -fsSL https://raw.githubusercontent.com/mpfaffenberger/code_puppy/main/scripts/install_termux.sh | bash -s -- --yes
```

### Step 1c — Testing a PR branch or git ref instead of a published package?

Use the **source-checkout** installer instead. This is the honest path for
branch/ref validation because it actually clones and runs the requested code.
It is not the same thing as installing the latest published package and hoping
nobody notices.

```bash
curl -fsSL https://raw.githubusercontent.com/mpfaffenberger/code_puppy/main/scripts/install_termux_checkout.sh | \
  bash -s -- --yes --repo-url https://github.com/mpfaffenberger/code_puppy.git --ref main --require-clean
```

That flow installs lean Termux prerequisites, clones the target ref, runs
`uv sync --no-dev`, and verifies `code-puppy` plus
`code-puppy-bootstrap` from the checkout itself.

### Step 2 — Prefer to drive it by hand?

Use this exact manual flow:

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

On a phone this auto-selects the **`android-termux-lean`** profile, which keeps
the install small by leaving heavy optional extras detached until you want them.

### Step 3 — Already have `uv` and want prompts?

Use the bootstrap wizard once `uvx` is available:

```bash
uvx --from code-puppy code-puppy-bootstrap wizard
```

That guided flow is great after `uv` exists, but it is not the true from-zero
installer because `uvx` itself has to exist first. Cute little bootstrap snake
eating its own tail otherwise.

## Optional — Android-native superpowers (DroidPuppy)

Only do this if you want phone-native capabilities: app launching, settings
routing, Brave/Chrome handoff, browser inspection, screenshots, and friendly
shortcuts.

### Step 1 — Get the DroidPuppy overlay

```bash
git clone https://github.com/kvandre12-commits/DroidPuppy
cd DroidPuppy
```

### Step 2 — Install the overlay into Code Puppy

```bash
python scripts/install_overlay.py
```

This drops the Android plugins into:

```text
~/.code_puppy/plugins/
```

so your existing Code Puppy picks them up automatically on next start.

### Step 3 — Restart Code Puppy and verify

```bash
code-puppy -i
```

Then run the DroidPuppy doctor check inside Code Puppy to confirm the Android
stack is healthy.

## Optional — attach extras you skipped

When you decide you *do* want browser/image/etc. on the device, inspect a
heavier profile first:

```bash
uvx --from code-puppy code-puppy-bootstrap plan --profile desktop-browser
```

Then run the reattach/install command it prints.

You can also drive deployment policy through a manifest override:

```bash
uvx --from code-puppy code-puppy-bootstrap plan \
  --profile android-termux-lean \
  --manifest-json '{"extras_add": ["durable"], "notes": ["Enable only after validating the device."]}'
```
