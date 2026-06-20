# PR Body: Android day-zero lean install path

## Summary

This PR makes Code Puppy friendlier to **lean installs**, especially on
Android/Termux, by moving optional capability stacks behind extras and ensuring
core imports degrade gracefully when those extras are not installed.

The practical goal is simple:

> a user should be able to install upstream Code Puppy, add the DroidPuppy
> overlay, and start using it on their phone the same day.

## Why

Code Puppy already has the right extension model for product layers like
DroidPuppy:

- built-in plugins
- user plugins in `~/.code_puppy/plugins/`
- project plugins in `<CWD>/.code_puppy/plugins/`

That means Android-native functionality does **not** need to be merged into
core. The engine should stay lean; platform-specific functionality can live in
a plugin overlay.

The blocker today is that `main` still pulls several optional stacks into the
mandatory dependency set, which makes the default install heavier and less
reliable than necessary for mobile environments.

## Current upstream blockers addressed by this branch

This branch moves or supports moving these optional dependency families out of
core install assumptions:

- provider SDKs (`openai`, `anthropic`, `azure-identity`, `boto3`)
- MCP support (`mcp`, `pydantic-ai-slim[mcp]`)
- browser automation (`playwright`)
- search/image/fuzzy extras (`ripgrep`, `Pillow`, `rapidfuzz`)

It also updates core code paths so missing optional dependencies fail
**gracefully** instead of breaking import-time behavior.

## What changed

### Dependency shape

- trims the default dependency graph
- moves optional capabilities behind explicit extras
- keeps the base install focused on the core engine

### Import/runtime behavior

- protects runtime paths from import-time crashes when optional stacks are absent
- makes MCP-specific behavior degrade cleanly when MCP extras are not installed
- keeps Android/Termux lean installs from tripping over desktop-heavy features

### Tests/docs

- adds regression coverage for optional dependency import behavior
- documents optional MCP installation explicitly
- adds an Android day-zero brief so the intended install shape is clear

## Why this is useful beyond Android

This is not Android special pleading.

A lean default install is good engineering in general:

- fewer mandatory dependencies
- fewer platform-specific install failures
- clearer separation between core engine and optional integrations
- easier packaging for constrained or minimal environments

Android/Termux just makes the pain obvious faster.

## Intended install path

### 1. Install upstream Code Puppy

```bash
uvx code-puppy
# or
pip install code-puppy
```

### 2. Add the Android overlay

```bash
git clone https://github.com/kvandre12-commits/DroidPuppy.git
cd DroidPuppy
python scripts/install_overlay.py
```

That installs DroidPuppy into Code Puppy's supported user plugin tier:

```text
~/.code_puppy/plugins/
```

### 3. Use it on-device

Start Code Puppy and run the DroidPuppy doctor / Android tool path.

## Why this should stay split

### Upstream Code Puppy should own

- lean default dependency graph
- graceful optional-import behavior
- stable plugin loading tiers
- generic runtime/tool integration seams
- upstream-quality tests

### DroidPuppy should own

- Android intents, settings, and app routing
- ADB/CDP/browser control helpers
- UI dump/input/screenshot/logcat/dumpsys tools
- Android setup/doctors/workflow product layer

That split keeps Code Puppy general-purpose while still enabling a serious
phone-native operator stack.

## Validation

This branch was validated with focused lint/test coverage around the optional
import paths and Android-friendly dependency shape.

## Reviewer takeaway

The ask here is not "merge DroidPuppy into core."

The ask is:

> keep upstream Code Puppy lean enough that platform-specific overlays can layer
> on cleanly, including a same-day Android/Termux path.
