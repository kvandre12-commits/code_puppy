# Android Validation Mutant Matrix

Target candidate:

- `validation-requires-bare-termux`

This is a **candidate**, not doctrine.

The goal is to isolate mechanism, not compress pain into a slogan.

## Candidate statement

> Android validation may require a bare/fresh Termux environment.

## Suspected mechanisms

Potential underlying mechanisms this candidate might actually be pointing at:

- PATH contamination
- Python version mismatch
- venv leakage / environment contamination
- missing native libraries
- missing build toolchain
- missing system packages
- permission / storage model differences
- source-checkout vs installed-tool path differences
- dev dependency pressure vs lean runtime path

## Mutant matrix

| Mutant | Expected result | Actual result | Notes / mechanism clues |
|---|---|---|---|
| Fresh Termux, minimal packages only | Pass | fail on published-package path | Mike Test 003 separate-phone clean run failed at `uv tool install --refresh code-puppy` while building `cryptography` / `maturin`; operator-reported clue: `Rust not found` |
| Fresh Termux + `ripgrep` installed | Pass | pass | System `rg` on PATH produced successful grep matches; hidden `rg` degraded gracefully |
| Fresh Termux + build tools (`rust`, `clang`) | Pass | pass-ish / needs strict reprompt | Earlier fresh-phone proof included `pkg install python git uv rust clang` before bootstrap; Mike Test 004 is the strict separate-phone reprompt for this exact mutant |
| Fresh Termux + active project venv | ? | mixed | Plain `uv sync` from fresh checkout with mismatched active `VIRTUAL_ENV` failed building `ruff`; this does not isolate venv as sole cause because lean venv install later passed |
| Fresh Termux + custom PATH overrides | ? | partial unknown | We do have one PATH mutant: hiding `rg` from PATH caused graceful degradation, not startup failure; broader Python/uv shadowing still untested |
| Fresh Termux + source checkout install path | ? | pass | Fresh upstream clone + upstream PR ref + documented lean source-checkout runtime path passed |
| Fresh Termux + `uv sync --no-dev` | Pass | pass | Documented Android source-checkout runtime path and `uv run --no-dev` help test both passed |
| Fresh Termux + plain `uv sync` | Likely fail or noisy | fail | Fresh checkout proof failed building `ruff` with Rust OOM, confirming dev-group pressure is hostile on Android |
| Long-lived dev environment | ? | mixed | Existing evidence labels long-lived dev environments as mixed/noisy; exact mechanism still unresolved |
| Samsung device / current Android | ? | pass-ish | Multiple successful proofs were on Samsung Android 16 / Termux, but that does not generalize to other devices yet |
| Different Android version or device family | ? | unknown | No comparative device-family matrix yet |

## Questions to answer

Do not ask:

- "What story explains the failure?"

Ask:

- What changed between pass and fail?
- Did PATH order change?
- Did Python interpreter selection change?
- Did dependency set change?
- Did build requirements appear?
- Did the runtime path switch from lean to dev/full?
- Did source checkout behavior differ from installed package behavior?

## Promotion rule

Promote this candidate only if repeated mutants support a mechanism-stable statement.

Examples of stronger eventual doctrines:

- Android validation must prefer lean runtime paths over dev sync paths.
- Android validation must control PATH and interpreter selection explicitly.
- Android validation must separate source-checkout proof from published-install proof.

Examples of weak premature slogans:

- bare Termux is required
- Android is flaky
- Playwright broke everything

## Desired outcome

Turn:

- symptom description

into:

- mechanism-aware doctrine

If the mechanism cannot be isolated, keep this as a candidate or reject it.
