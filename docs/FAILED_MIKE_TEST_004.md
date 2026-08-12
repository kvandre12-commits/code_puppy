# Failed Mike Test 004

**Status:** failed
**Source run sheet:** `docs/MIKE_TEST_RUN_004.md`
**Operator prompt:** `docs/MIKE_TEST_OPERATOR_PROMPT_004.md`

## Provenance

- Device:
- Android version:
- Termux version:
- Target class: upstream main
- Repo URL:
- Branch/ref:
- Commit SHA:
- Install surface: published-package
- Evidence source: clean run
- Contamination state: clean unless proven otherwise

## Baseline package state

```text
```

## First meaningful failure

- Exact command: `uv tool install --refresh code-puppy`
- Error output: operator-reported failure while downloading/building `rpds-py==2026.5.1` and build-system requirements
- Failure step: published-package install
- Full log path:

```text
Failed to download and build `rpds-py==2026.5.1`
├─▶ Failed to install requirements from `build-system.requires`
├─▶ Failed to build `maturin==1.14.1`
├─▶ The build backend returned an error
╰─▶ Call to `bootstrap.build_wheel` failed (exit status: 1)

[stdout]
Rust not found, installing into a temporary directory

[stderr]
/data/data/com.termux/files/home/.cache/uv/builds-v0/.tmppp9BCt/lib/python3.13/site-packages/setuptools/_vendor/wheel/bdist_wheel.py:4:
FutureWarning: The wheel package is no longer the canonical location of the bdist_wheel command, and will be removed in a future release.
Please update to setuptools v70.1 or later which contains an integrated version of this command.

Python reports SOABI: cpython-313-aarch64-linux-android
Computed rustc target triple: aarch64-unknown-linux-android
Target triple not supported by rustup: aarch64-unknown-linux-android

hint: `rpds-py` (v2026.5.1) was included because `code-puppy` (v0.0.171)
depends on `pydantic-ai` (v2.0.0) which depends on
`pydantic-ai-slim[mcp]` (v2.0.0) which depends on
`fastmcp-slim[client]` (v3.4.2) which depends on
`mcp` (v1.28.0) which depends on `jsonschema` (v4.26.0)
which depends on `rpds-py`
```

## Hidden dependency exposed

```text
This failure is not just about `cryptography`. The published-package Android install path is also hitting a Rust-backed build for `rpds-py` through the `mcp -> jsonschema -> rpds-py` chain.

Candidate mechanisms now include:
- missing or unsupported Rust toolchain behavior on Android/Termux
- `rustup` target support mismatch for `aarch64-unknown-linux-android`
- broader inability to rely on source-building Rust-backed Python packages on this Termux target
- published-package dependency drift

Important target clue:
- the operator error reports `code-puppy` version `0.0.171`
- the current repo `pyproject.toml` declares version `0.0.569`

So this run is exercising an older published package lineage, not the current local repo state. That means the published-package acceptance path and upstream-repo-main state are currently not the same target in practice.
```
