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

## Base install

### Step 0 — Get Termux properly

Install **Termux from F-Droid or GitHub**, not the Play Store version (that one
is stale). Then update it:

```bash
pkg update && pkg upgrade
```

### Step 1 — Install the basics Termux needs

```bash
pkg install python git
```

### Step 2 — Install uv (recommended installer)

```bash
pkg install uv
```

If `pkg install uv` is unavailable on your Termux, use the official installer:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 3 — Let the bootstrap planner inspect your device

This installs nothing; it only inspects the environment.

```bash
uvx --from code-puppy code-puppy-bootstrap detect --json
```

### Step 4 — Get the recommended lean install plan

```bash
uvx --from code-puppy code-puppy-bootstrap plan --profile auto
```

On a phone this auto-selects the **`android-termux-lean`** profile, which keeps
the install small by leaving heavy optional extras detached until you want them.

### Step 5 — Install the recommended system packages

```bash
pkg install ripgrep proot
```

### Step 6 — Install Code Puppy (lean)

```bash
uv tool install --refresh code-puppy
```

### Step 7 — Run it

```bash
code-puppy -i
```

You now have a working, lean Code Puppy on Android.

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
