# Code Puppy / DroidPuppy Checkout Ownership

## What this repo is

This checkout is a Code Puppy working fork with a DroidPuppy Android overlay.

It owns agent runtime infrastructure and Android utility/orchestration tooling.
It does not own SharpEdge trading truth.

## Owns

### Code Puppy core

- Agent runtime.
- Tool/plugin framework.
- Callback/plugin loading.
- Model/provider plumbing.
- Workflow runtime support.

### DroidPuppy overlay

- Android intent helpers.
- Browser handoff utilities.
- ADB/CDP helper tools.
- UI dump/input/screenshot/logcat/dumpsys helpers.
- Android workflow feasibility and support bundles.
- Experimental orchestra abstractions and contracts.

## Does not own

- SharpEdge signal generation.
- Trade Gate analytics.
- Native SharpEdge Android UI rendering.
- Robinhood broker policy/routing.
- Broker credentials.
- Autonomous live order execution.

## Stable source areas

```text
code_puppy/
DroidPuppy/
tests/
docs/
README.md
OWNERSHIP.md
```

## Generated/runtime artifact areas

```text
outputs/
coverage.json
__pycache__/
.pytest_cache/
```

Treat generated runtime outputs as evidence, not source design.

## Boundary with SharpEdge

SharpEdge decides **what** should happen.

DroidPuppy helps with **how Android actions/observations can be performed**.

SharpEdge-Android owns the primary viewer. DroidPuppy/Brave/CDP is optional debug
or execution tooling, not the foundation for rendering the Trade Gate.

## Tests

Use the repo's configured Python test tooling. For Android-specific changes,
prefer focused tests around the plugin/tool touched rather than running unrelated
provider suites.

## Agent entrypoints

Read first:

1. `OWNERSHIP.md`
2. `docs/REPO_INVENTORY.md`
3. `DroidPuppy/README.md` if touching Android tooling
4. `DroidPuppy/contracts/README.md` if touching orchestration contracts
5. `code_puppy/callbacks.py` only if touching plugin hooks

Then work only inside Code Puppy/DroidPuppy infrastructure unless the task
explicitly points to a SharpEdge repo.
