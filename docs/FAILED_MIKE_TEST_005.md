# Failed Mike Test 005

**Status:** failed
**Source run sheet:** `docs/MIKE_TEST_RUN_005.md`
**Operator prompt:** `docs/MIKE_TEST_OPERATOR_PROMPT_005.md`

## Provenance

- Device:
- Android version:
- Termux version:
- Target class: corrected published artifact
- Repo URL: `https://github.com/mpfaffenberger/code_puppy.git`
- Published package version under test:
- Published wheel filename/SHA256 under test:
- Branch/ref:
- Commit SHA:
- Install surface: published-package exact-version pin
- Evidence source: clean run
- Contamination state: clean unless proven otherwise

## Baseline package state

```text
```

## First meaningful failure

- Exact command:
- Error output:
- Failure step:
- Full log path:

```text
```

## Artifact identity checks

Record these exactly if observed:

- `code-puppy` version actually resolved/installed:
- wheel filename actually under test:
- wheel SHA256 under test:
- whether the error text references a different package version than expected:
- whether the error text references a dependency chain that should have remained optional:

```text
```

## Hidden dependency exposed

```text
Describe the first real blocker, not the rescue path.

Good examples:
- corrected published artifact still leaked an optional-heavy dependency into base install
- the exact version pin did not install the artifact we intended to test
- Android compatibility still has a remaining blocker unrelated to the earlier packaging drift

If relevant, say explicitly whether the failure is:
- artifact mismatch
- dependency-graph leak
- platform compatibility issue
- operator contamination
```

## Best current interpretation

```text
State what this failed run actually proves.
Do not overclaim.
Examples:
- "Run 005 shows the corrected published artifact still leaks dependency X into base install."
- "Run 005 did not test the intended artifact because the resolved package version/output disagreed with the pinned target."
- "Run 005 reached a new blocker after the earlier packaging issue was removed."
```
