# Android Day-Zero Upstream Brief

## Goal

A user should be able to:

1. install **upstream Code Puppy**
2. add the **DroidPuppy overlay**
3. use it on their Android phone **that day**

without forking the engine, editing site-packages, or dragging desktop-only
optional dependencies into the default mobile install.

## Why this matters

Code Puppy already has the right extension model:

- built-in plugins
- user plugins in `~/.code_puppy/plugins/`
- project plugins in `<CWD>/.code_puppy/plugins/`

That means Android-native functionality does **not** need to live in Code Puppy
core. The engine should stay lean; the Android product layer should be an
overlay.

## Current upstream blockers

As of `origin/main`, the default dependency set still pulls in optional stacks
that make Android/Termux installs heavier and less reliable than they need to
be.

### Current core dependency blockers

- `pydantic-ai-slim[openai,anthropic,mcp]`
- `mcp`
- `openai`
- `anthropic`
- `azure-identity`
- `boto3`
- `rapidfuzz`
- `ripgrep`
- `playwright`
- `Pillow`

These are all valid features, but they should not be part of the mandatory
phone-first install path.

## Proposed upstream shape

Core install should be lean and import-safe by default.

Optional capability families should live behind extras:

- `openai`
- `anthropic`
- `azure`
- `bedrock`
- `mcp`
- `browser`
- `images`
- `fuzzy`
- `search`

And core modules should keep importing cleanly when those extras are absent.

## What this branch already proves

This follow-up branch (`upstream-lean-provider-extras`) now demonstrates that
shape in reviewable pieces.

### Already done on this branch

- provider SDKs moved behind extras
- browser deps moved behind extras
- MCP moved behind extras
- core imports now degrade gracefully when optional stacks are missing
- README updated to document optional MCP install
- regression tests added for missing optional dependencies

### Relevant commits on this branch

- `6c27307` — Make provider SDKs optional for lean installs
- `e1d8367` — test(core): cover optional dependency lazy imports
- `866444c` — build: make MCP support optional for lean installs

## The intended operator path

### Step 1 — upstream engine

Install Code Puppy from upstream:

```bash
uvx code-puppy
# or
pip install code-puppy
```

### Step 2 — Android overlay

Install DroidPuppy as a plugin overlay:

```bash
git clone https://github.com/kvandre12-commits/DroidPuppy.git
cd DroidPuppy
python scripts/install_overlay.py
```

That installs into:

```text
~/.code_puppy/plugins/
```

which Code Puppy already supports natively.

### Step 3 — phone validation

Launch Code Puppy and run the Android doctor path to verify:

- Android command availability
- browser presence
- optional ADB/CDP readiness
- installed DroidPuppy plugin inventory

## What should stay upstream vs. overlay

### Upstream Code Puppy

Owns:

- lean default dependency graph
- graceful optional-import behavior
- stable plugin loading tiers
- generic agent/runtime/tool seams
- upstream-reviewable tests

### DroidPuppy overlay

Owns:

- Android intent helpers
- browser handoff
- ADB/CDP helpers
- UI dump/input/screenshot/logcat/dumpsys tools
- Android workflow/orchestration product layer
- Android-specific docs, doctors, and operator flows

## Bottom line

The ask is not "merge DroidPuppy into core."

The ask is:

> make upstream Code Puppy lean enough that Android users can install the engine,
> add the DroidPuppy overlay, and start using a serious phone-native agent stack
> the same day.
