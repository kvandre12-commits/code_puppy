# Code Puppy on Android (Termux)

This is the canonical install flow for running Code Puppy on a phone with
Termux. It keeps the install lean by default and lets you attach optional
capabilities later, only if you actually want them.

## Mental model

- Code Puppy is the engine. It installs lean on Android via the bootstrap planner.
- DroidPuppy is an optional Android-native overlay. It is layered on after Code Puppy is installed.
- Extras (browser/image/fuzzy/search/provider) are opt-in, not mandatory.

## Base install

### Step 0 — Get real Termux

Install Termux from F-Droid or GitHub, not the Play Store build. Then update it:

```bash
pkg update && pkg upgrade
```

### Step 1 — Install the basics

```bash
pkg install python git
```

### Step 2 — Install uv

```bash
pkg install uv
```

If that package is unavailable on your device, use:

```bash
pip install uv
```

### Step 3 — Inspect the device without installing anything

```bash
uvx --from code-puppy code-puppy-bootstrap detect --json
```

### Step 4 — Get the recommended lean plan

```bash
uvx --from code-puppy code-puppy-bootstrap plan --profile auto
```

On Termux this auto-selects `android-termux-lean`, which keeps the initial
attach small by leaving heavy optional extras detached.

### Step 5 — Install the recommended native packages

```bash
pkg install rust clang ripgrep proot
```

Why the extra toolchain?

- `pydantic-core` is a required dependency of `pydantic`.
- Android/Termux does not currently get a prebuilt wheel for that package.
- A fresh phone may need to build it locally, which means `rust` and `clang`
  are part of the honest readiness story.

The base Android path still stays lean by keeping optional extras detached:

- browser automation stays in `[browser]`
- image support stays in `[images]`
- fuzzy/search/provider extras stay opt-in

### Step 6 — Install Code Puppy lean

```bash
uv tool install --refresh code-puppy
```

### Step 7 — Run it

```bash
code-puppy -i
```

## One-command guided path

If you want the bootstrap flow to prompt/verify each step:

```bash
uvx --from code-puppy code-puppy-bootstrap wizard
```

For automation/non-interactive setup:

```bash
uvx --from code-puppy code-puppy-bootstrap wizard --yes
```

## Optional — attach the DroidPuppy overlay

Only do this if you want Android-native capabilities like app launching,
settings routing, browser handoff, screenshots, or UI helpers.

```bash
git clone https://github.com/kvandre12-commits/DroidPuppy
cd DroidPuppy
python scripts/install_overlay.py
```

That installs the overlay into:

```text
~/.code_puppy/plugins/
```

Restart Code Puppy and verify with the in-app Droid diagnostics.

## Optional — attach heavier extras later

Inspect a richer profile first:

```bash
uvx --from code-puppy code-puppy-bootstrap plan --profile desktop-browser
```

You can also add extras through a manifest override:

```bash
uvx --from code-puppy code-puppy-bootstrap plan \
  --profile android-termux-lean \
  --manifest-json '{"extras_add": ["durable"], "notes": ["Enable only after validating the device."]}'
```
