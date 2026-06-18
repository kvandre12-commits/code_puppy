# Code Puppy Ownership

## What this repo is

Code Puppy is the agent runtime and plugin framework.

It provides the general coding-agent engine that can work across repos. It is
not itself the SharpEdge trading system.

## Owns

- Agent runtime.
- Plugin and callback framework.
- Model/provider plumbing.
- Tool execution wrappers.
- Agent/session/storage mechanics.
- Core Code Puppy docs and tests.

## Does not own

- SharpEdge signal generation.
- Trade Gate analytics.
- Native SharpEdge Android rendering.
- Robinhood broker command policy.
- DroidPuppy Android overlay work unless present on a dedicated branch/checkout.
- Project-specific generated artifacts from other repos.

## Stable source areas

```text
code_puppy/
tests/
docs/
README.md
AGENTS.md
OWNERSHIP.md
pyproject.toml
```

## Generated/runtime artifact areas

```text
coverage.json
__pycache__/
.pytest_cache/
```

## Boundary with SharpEdge repos

Use Code Puppy to edit SharpEdge repos, but do not put SharpEdge domain logic in
Code Puppy core. If SharpEdge needs a Code Puppy extension, prefer a plugin or a
project-level plugin rather than modifying core command-line code.

## Tests

Use the repo's Python test/lint tooling. For new plugin behavior, add focused
plugin tests instead of broad unrelated changes.

## Agent entrypoints

Read first:

1. `OWNERSHIP.md`
2. `AGENTS.md`
3. `README.md`
4. `code_puppy/callbacks.py` only if touching plugin hooks

Then keep changes inside Code Puppy runtime/plugin boundaries.
