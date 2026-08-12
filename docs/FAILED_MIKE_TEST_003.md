# Failed Mike Test 003

**Status:** failed
**Source run sheet:** `docs/MIKE_TEST_RUN_003.md`
**Operator prompt:** `docs/MIKE_TEST_OPERATOR_PROMPT_003.md`

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
- Error output: operator-reported failure while downloading/building `tree-sitter-typescript==0.23.2`
- Failure step: published-package install
- Full log path:

```text
Failed to download and build `tree-sitter-typescript==0.23.2`
The build backend returned an error while compiling the package
Compilation failed because `tree_sitter/parser.h` was unavailable

Important dependency clue:
- this artifact failure refers to `tree-sitter-typescript==0.23.2`
- because published `code-puppy==0.0.171` depends on it
```

## Hidden dependency exposed

```text
This failure points to published-package dependency drift rather than a generic Android compiler problem. The published artifact being exercised in this run still pulls `tree-sitter-typescript==0.23.2` into the base install path because `code-puppy==0.0.171` declares it as an unconditional dependency.

Candidate mechanism:
- published artifact dependency graph does not match current repository intent
- optional/heavy functionality was flattened into base install in older published lineage
- the clean Android install path is therefore failing against an old published package contract, not necessarily against current repo dependency modeling

Important target clue:
- the operator failure references `code-puppy==0.0.171`
- the current repo `pyproject.toml` declares version `0.0.569`

So this run is exercising an older published package lineage, not the current local repo state.
```