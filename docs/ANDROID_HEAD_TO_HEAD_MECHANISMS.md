# Android Head-to-Head Mechanisms

This note compares two competing explanations for the Android validation split.

It is intentionally prediction-first.

Do **not** ask which slogan feels truer.
Ask which explanation survives more mutants.

For current status/confidence labels, defer to `docs/ANDROID_CANDIDATE_DECISIONS.md`.
This note exists to compare predictions and evidence, not to outrank the ledger.

---

## The buckets

### Known true
- desktop-only dependencies must degrade gracefully on Android
- browser capabilities are optional, not foundational
- missing tooling should degrade gracefully, not kill startup
- lean/bootstrap Android install paths can succeed

### Known false
- validation-requires-system-python
- remove-playwright-and-android-is-fixed
- browser-automation-never-works-on-android

### Unknown but testable
- validation-prefers-lean-runtime-paths
- avoid-unnecessary-native-build-pressure
- validation-requires-clean-path-ordering
- validation-requires-no-venv-contamination
- validation-requires-source-vs-installed-boundary

---

## Competing candidates

### Candidate A
`validation-prefers-lean-runtime-paths`

**Claim:** validation succeeds more often when the runtime path stays lean.

**Core prediction:**
If the environment becomes leaner, success rate should improve even when native
build pressure is otherwise unchanged.

**Predictions this candidate must own:**
- Large environment + prebuilt wheels only should still be less reliable than a lean path.
- Lean environment + forced Rust/native build should still be relatively favorable or mixed, not catastrophically bad by default.
- Removing compile steps should help, but lean-ness itself should continue to matter after compile pressure is controlled.

### Candidate B
`avoid-unnecessary-native-build-pressure`

**Claim:** the main failure driver is avoidable native compilation/build churn,
not lean-ness itself.

**Core prediction:**
If native build pressure is removed, validation should succeed even when the
environment is otherwise larger or less lean.

**Predictions this candidate must own:**
- Large environment + prebuilt wheels only should pass more often than the lean-path slogan predicts.
- Lean environment + forced Rust/native build should fail or become unreliable.
- Removing compile steps should improve reliability even if the environment remains broad.

---

## Current evidence (existing observations only)

| Observation | Supports A | Supports B | Weight | Notes |
|---|---|---|---|---|
| `uv sync --no-dev` passed | yes | yes | medium | Lean and low-build-pressure co-occurred, so this supports both but separates neither |
| clean lean venv install passed | yes | maybe | medium | Lean path helped, but the stronger implication is that a clean venv can pass without proving system-Python or bare-Termux slogans |
| plain `uv sync` failed building `ruff` with Rust OOM | maybe | strongly | high | Direct causal chain: native build workload -> Rust compile -> OOM -> validation failure |
| upstream dependency audit still flagged heavy provider/native stack as Android risk | weakly | yes | medium | Suggests broad/native burden matters, especially when it can trigger build or resource pressure |
| missing `ripgrep` degraded gracefully | weakly | no | low | Helpful Android resilience evidence, but not strong evidence for either competing validation mechanism |
| missing Playwright degraded gracefully after patch | weakly | no | low | Again, valuable doctrine elsewhere, but only weakly relevant here |
| published/install-tool bootstrap path viable | maybe | maybe | low-medium | Shows an alternate path can succeed, but does not yet split lean-ness from build pressure |
| system Python not required | neutral | neutral | low | Important falsification for another candidate, but mostly removes a distraction rather than helping A or B |

### Current scorecard

This is intentionally rough and qualitative, not fake-precise.

- Candidate A (`validation-prefers-lean-runtime-paths`): **confidence = medium**
- Candidate B (`avoid-unnecessary-native-build-pressure`): **confidence = medium-high**

### Why Candidate B is currently ahead

It explains the strongest failure we have actually observed:

- plain `uv sync`
- `ruff` native/Rust build kicks in
- Rust OOM
- validation/install path fails

That is a much tighter causal chain than the current support for “lean-ness” by itself.

### Why Candidate A still survives

Lean paths have repeatedly passed, and that may still matter even after build
pressure is controlled. But right now many successful runs are both:

- lean
- low native build pressure

So Candidate A is still alive, just not entitled to the crown yet.

### Current epistemic status

The variables are still confounded.
Right now, **lean** and **low native build pressure** mostly travel together.
That means current evidence is useful, but causally sloppy.

---

## Variable-splitting mutant table

The point of these mutants is to separate:

- environment lean-ness
- native build pressure

| Mutant | Lean? | Native build pressure? | Expected by A | Expected by B | Actual result | Notes |
|---|---|---:|---|---|---|---|
| `uv sync --no-dev` on fresh checkout | yes | low | pass | pass | pass | existing evidence |
| plain `uv sync` on fresh checkout | no | high | fail or noisy | fail | fail | existing evidence; `ruff` build OOM |
| large environment, prebuilt wheels only | no | low | maybe fail / mixed | pass | ? | high-value splitter |
| lean environment, forced Rust/native build | yes | high | pass or mixed | fail | ? | high-value splitter |
| large env, no compile steps, optional extras already resolved | no | low | maybe mixed | pass | ? | similar to B-friendly world |
| lean env, dev group attached but prebuilt/no compile | yes | low-medium | pass | pass or mixed | ? | can test whether dev-group alone hurts or only compile spikes hurt |
| long-lived dev env with dev sync but cached/prebuilt artifacts | no | low-medium | maybe mixed | pass or mixed | ? | helps separate residue from build pressure |

---

## Better mechanism-level questions

Instead of asking:
- Are lean paths better?

Ask:
- Does failure still occur when the environment is large but no native compile happens?
- Does failure appear when the environment is lean but a Rust/native compile is forced?
- Is the real hazard dev-group expansion?
- Is the real hazard compile-time memory pressure?
- Is the real hazard broad dependency graphs only when they trigger source builds?

---

## Promotion rule

Promote only when one candidate survives variable-splitting mutants better than
the other.

### Promote Candidate A if
Success tracks lean-ness even after native build pressure is controlled.

### Promote Candidate B if
Success tracks removal of native build pressure even when the environment stays
relatively broad.

### Keep both candidates active if
Different mutant families support different mechanisms.
In that case, the future doctrine may need to be narrower, such as:

- Android validation must avoid unnecessary native compilation during runtime proof.
- Android validation should prefer lean runtime paths when dependency/build surfaces are uncertain.

---

## Anti-folklore rule

Do not promote:
- the slogan with the best vibe
- the explanation that arrived first
- the explanation that matched the most painful failure

Promote:
- the explanation that made the best predictions and survived attack
