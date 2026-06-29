# Shipping Android from Main Code Puppy

## Short version

If you want to share the Android work, start from **main Code Puppy**.

That is the engine, the installer surface, and the honest entry point.

Then, if you want phone-native actions, attach **DroidPuppy** as the optional
Android overlay.

Do **not** make the reviewer guess which repo is the product, which repo is the
engine, or which install path is actually under test. That is how signal goes to
live in a ditch.

## The clean story

### 1. Code Puppy main is the launch surface

Code Puppy owns:

- the published install path
- the Android/Termux onboarding scripts
- the lean bootstrap planner
- branch/ref checkout validation
- the general plugin architecture that makes the Android overlay possible

### 2. DroidPuppy is the optional Android overlay

DroidPuppy owns the phone-native layer:

- Android app/settings actions
- browser handoff and CDP helpers
- screenshots, UI, support bundles, and Android-specific workflows

The Android story should therefore be told in this order:

```text
main Code Puppy
  -> lean Android install / onboarding
  -> optional DroidPuppy attach
  -> Android-native demo
```

## Use the right install path

### Published-artifact / fresh-user path

If you are showing what a normal Android user can do from main Code Puppy,
start here:

```bash
curl -fsSL https://raw.githubusercontent.com/mpfaffenberger/code_puppy/main/scripts/onboard_android.sh | bash -s -- --yes
```

That path is the cleanest main-first story because it owns:

- lean Code Puppy install
- optional DroidPuppy attach
- adb detection/install
- staged readiness summary

### Branch/ref/main-checkout proof path

If you are trying to prove a branch, ref, or checkout — including `main` as a
specific repo state — use the source-checkout installer instead:

```bash
curl -fsSL https://raw.githubusercontent.com/mpfaffenberger/code_puppy/main/scripts/install_termux_checkout.sh | \
  bash -s -- --yes --repo-url https://github.com/mpfaffenberger/code_puppy.git --ref main --require-clean
```

That is the honest path when the question is:

> does this checked-out Code Puppy state work on Android?

not:

> does the latest published package happen to work today?

## Main-first share packet

If you want a compact share/demo from main Code Puppy, use this sequence.

### Step 1 — show the main install lane

Point to one of these from the root repo:

- `README.md` Android / Termux section
- `docs/ANDROID.md`
- `scripts/onboard_android.sh`
- `scripts/install_termux_checkout.sh`

This proves the Android story begins in Code Puppy main, not in a side repo.

### Step 2 — show the engine attached on Android

Use one of these receipts:

- onboarding summary from `scripts/onboard_android.sh`
- bootstrap plan output from:

```bash
uvx --from code-puppy code-puppy-bootstrap plan --profile auto --json
```

What this proves:

- Code Puppy understands Android/Termux directly
- the install path is lean by default
- optional capabilities are policy-gated instead of welded in

### Step 3 — optionally attach the Android overlay

If you want phone-native actions, then attach DroidPuppy:

```bash
git clone https://github.com/kvandre12-commits/DroidPuppy
cd DroidPuppy
python scripts/install_overlay.py
```

Restart Code Puppy and use the DroidPuppy tools from there.

### Step 4 — show one Android-native action

After the overlay is attached, the cleanest demo is:

- `droidpuppy_doctor(deep=False)`
- `android_open(target="wifi")`

Optional browser depth:

- `android_brave_status()`
- `android_cdp_doctor()`

What this proves:

- the engine shipped from main Code Puppy
- the overlay attached cleanly through the plugin contract
- the phone responds as a first-class operator surface

## The sentence to use

> Code Puppy main is the engine and Android install surface; DroidPuppy is the optional Android-native overlay; and the Android story should be shared in that order.

## What not to do

- do not start the story inside DroidPuppy if the install lane starts in Code Puppy
- do not use the published-package installer as fake proof for a branch/ref claim
- do not mix clean-install acceptance evidence with live Android-surface demo as if they are one thing
- do not bury the reviewer in contaminated-run archaeology unless they specifically ask for it

## Deeper evidence, if needed

If someone wants the fuller Android acceptance trail from main Code Puppy, send:

- `docs/ANDROID.md`
- `docs/ANDROID_MIKE_TEST_PROVENANCE.md`
- `docs/MIKE_TEST_RUN_001.md`
- `docs/CONTAMINATED_MIKE_TEST_001.md`
