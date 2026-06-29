# Android Build + Handoff Playbook

Use this when the goal is not just "Android kinda works here," but:

> ship a reproducible Android-ready repo state to another human without making
> them reverse-engineer the lane.

## Pick the right lane

### Lane A — published artifact / fresh-user Android proof

Use this when the claim is:

> the currently published Code Puppy artifact is installable from Android/Termux

Run:

```bash
curl -fsSL https://raw.githubusercontent.com/mpfaffenberger/code_puppy/main/scripts/onboard_android.sh | \
  bash -s -- --yes --version <pypi-version>
```

Good examples:

- release acceptance
- clean-user onboarding proof
- "what does Android get from main Code Puppy right now?"

### Lane B — branch/ref/checkout Android proof

Use this when the claim is:

> this exact repo state / PR / branch works on Android

Run:

```bash
curl -fsSL https://raw.githubusercontent.com/mpfaffenberger/code_puppy/main/scripts/install_termux_checkout.sh | \
  bash -s -- --yes --repo-url <repo-url> --ref <git-ref> --require-clean
```

Good examples:

- PR validation
- pre-merge Android proof
- handoff to another operator testing a specific branch

### Lane C — optional Android-native overlay attach

Use this after A or B when you want DroidPuppy-native actions:

```bash
git clone https://github.com/kvandre12-commits/DroidPuppy
cd DroidPuppy
python scripts/install_overlay.py --overwrite
```

That is not the engine install lane. It is the optional phone-native layer.

## Pre-push repo checks

Run these from the Code Puppy repo before declaring Android handoff-ready:

```bash
ruff check .
ruff format --check .
pytest -q \
  tests/test_android_onboarding_script.py \
  tests/test_termux_installer_script.py \
  tests/test_termux_checkout_installer_script.py \
  tests/test_packaging_metadata.py \
  tests/plugins/test_android_capability_graph_kit.py \
  tests/plugins/test_android_capability_runtime_truth.py \
  tests/plugins/test_android_paginated_crawl_kit.py
```

If you want the broader Android/governance/operator slice too:

```bash
pytest -q \
  tests/plugins/test_authority_gateway.py \
  tests/plugins/test_authority_gateway_tooling.py \
  tests/plugins/test_project_os_supervisor.py \
  tests/test_droidpuppy_context_kit.py \
  tests/test_droidpuppy_context_commands.py \
  tests/test_droidpuppy_context_repo_governance.py \
  tests/test_mcp_init.py \
  tests/test_provider_credentials.py \
  tests/tools/test_tools_init.py \
  tests/test_cli_runner_coverage.py \
  tests/test_cli_runner_full_coverage.py \
  tests/plugins/test_android_media_router.py \
  tests/test_callbacks_extended.py \
  tests/test_android_onboarding_script.py \
  tests/test_termux_installer_script.py \
  tests/test_termux_checkout_installer_script.py \
  tests/test_packaging_metadata.py
```

## Release-artifact sanity check

If the handoff is about a published or soon-to-be-published wheel, also verify
that the built wheel keeps optional-heavy dependencies out of base:

```bash
python -m build --wheel --outdir dist/
python scripts/check_wheel_metadata.py --pyproject pyproject.toml dist/code_puppy-*.whl
```

That check matters because Android/Termux should stay lean by default instead of
accidentally dragging native-heavy junk into the base install.

## What to hand another human

A decent Android handoff packet should include:

1. **which lane to run**
   - published artifact
   - checkout/ref proof
   - optional overlay attach
2. **exact command**
3. **exact version/ref**
4. **whether `--require-clean` is expected**
5. **expected success shape**
   - onboarding summary
   - `code-puppy --help`
   - bootstrap detect/plan output
6. **optional follow-up**
   - overlay attach
   - Wireless Debugging pairing
   - browser/CDP probe

## Minimal handoff template

```text
Android handoff lane: <published-artifact|checkout-ref>
Repo/package target: <pypi version or git ref>
Command: <exact command>
Clean-run requirement: <yes|no>
Overlay expected: <yes|no>
Expected proof: <summary / detect / plan / code-puppy --help>
Next optional step: <overlay attach / adb pair / cdp probe>
```

## Receipts that are worth saving

For a real operator handoff, save at least one of:

- onboarding summary output from `scripts/onboard_android.sh`
- checkout validation output from `scripts/install_termux_checkout.sh`
- `uvx --from code-puppy code-puppy-bootstrap detect --json`
- `uvx --from code-puppy code-puppy-bootstrap plan --profile auto --json`

If the point is Android-native depth, also save:

- DroidPuppy overlay install output
- `droidpuppy_doctor(deep=False)` result
- `android_cdp_doctor()` / `android_cdp_probe(...)` result if browser depth matters

## The boring truth we want reviewers to understand

- **Code Puppy main** is the Android install/build surface.
- **DroidPuppy** is the optional Android-native overlay.
- **Published-artifact proof** and **checkout/ref proof** are different claims.
- If you mix those claims together, your handoff packet becomes lying with extra steps.
