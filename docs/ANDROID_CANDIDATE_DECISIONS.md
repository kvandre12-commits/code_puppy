# Android Candidate Decisions

This ledger separates **evidence**, **candidate doctrine**, and **promoted doctrine**.

Rule of thumb:

- **Evidence** = artifacts, branches, logs, failed installs, validation runs
- **Candidate decision** = plausible lesson inferred from repeated evidence
- **Promoted doctrine** = lesson that survived multiple Android mutants/challenges
- **Rejected doctrine** = plausible lesson that failed to generalize

This keeps us from accidentally promoting every bruise into wisdom.

**Canonical-status rule:** when Android evidence docs disagree on candidate posture,
this ledger is the current source of truth for status, confidence, blockers, and
next discriminating mutant.

---

## Current promoted doctrine

| Candidate decision | Evidence count | Challenges | Status | Notes |
|---|---:|---:|---|---|
| desktop-deps-degrade-gracefully | 7+ | passed | promoted | Stored as `android-desktop-deps-degrade-gracefully` |
| bootstrap-uses-lean-install-path | 6+ | passed | promoted | Stored as `android-bootstrap-uses-lean-install-path` |
| browser-capabilities-are-optional | 5+ | passed | promoted | Stored as `android-browser-capabilities-are-optional` |
| missing-tooling-triggers-degradation | 5+ | passed | promoted | Stored as `android-missing-tooling-triggers-degradation` |

---

## Active candidates

| Candidate decision | Evidence count | Challenges | Status | Why still candidate |
|---|---:|---:|---|---|
| android-native-first | 3 | pending | active candidate | Strong instinct, but may be too broad; needs proof it survives outside install/bootstrap pain |
| path-assumptions-are-fragile | 3 | pending | active candidate | PATH weirdness clearly hurt Android flows, but may be a broader environment rule, not Android-only doctrine |
| validation-requires-bare-termux | 4 | decomposed | umbrella / suspect candidate | Keep only as an umbrella label for the evidence stream. Too coarse to promote until child mechanisms are tested. See decomposition below and `docs/ANDROID_VALIDATION_MUTANT_MATRIX.md`. |
| capabilities-over-dependencies | 4 | pending | active candidate | Good abstraction, but needs more proof across non-browser optional surfaces |
| installers-must-assume-absence | 4 | pending | active candidate | Likely durable, but overlaps with missing-tooling degradation and lean bootstrap doctrine |
| avoid-unnecessary-native-build-pressure | 2 | pending | leading candidate | Currently ahead of `validation-prefers-lean-runtime-paths`, but not in promotion review yet |

### Candidate decomposition: `validation-requires-bare-termux`

Parent candidate posture:

- **Status:** umbrella / suspect candidate
- **Promotion rule:** do not promote the parent slogan unless no narrower child mechanism explains the evidence better
- **Main attack plan:** `docs/ANDROID_VALIDATION_MUTANT_MATRIX.md`
- **Reason for suspicion:** “bare Termux” sounds like an environment label, not a mechanism

#### Child candidates

| Child candidate | Status | Confidence | Evidence | Counter-evidence | Competing explanation | Promotion blockers | Next discriminating mutant |
|---|---|---|---|---|---|---|---|
| validation-requires-system-python | rejected | falsified | Fresh upstream PR-ref proof explicitly succeeded with Termux system Python (`/data/data/com.termux/files/usr/bin/python3.13`) | Clean lean venv proof also succeeded using `/data/data/com.termux/files/home/code_puppy_backup_20260617/.venv/bin/python`, so interpreter origin is not the controlling variable | N/A | Already failed its claim as stated | None; only reopen if new contradictory evidence appears |
| validation-requires-clean-path-ordering | active candidate | low-medium | Base Termux PATH with system `rg` worked; hiding `rg` from PATH degraded gracefully instead of crashing startup | No isolated proof yet that PATH contamination alone caused validation failure | avoid-unnecessary-native-build-pressure; validation-requires-no-venv-contamination | PATH evidence is still too indirect; current failures also fit build-pressure/dev-sync stories better | Large environment + shadowed Python/uv + low compile pressure |
| validation-requires-no-venv-contamination | active candidate | medium-low | Fresh proofs were cleaner; plain `uv sync` from fresh checkout while unrelated `VIRTUAL_ENV` was present failed building `ruff` | A clean lean venv on the same interpreter path passed, so “venv exists = fail” is false | avoid-unnecessary-native-build-pressure | Venv contamination may be incidental or interacting with dev-group pressure rather than causal | Long-lived dev env with clean prebuilt artifacts and active venv |
| validation-prefers-lean-runtime-paths | active candidate | medium | `uv sync --no-dev` / lean source path passed; clean lean venv install passed | Current wins may be explained by reduced native build pressure rather than lean-ness itself | avoid-unnecessary-native-build-pressure | Lean and low-build-pressure variables remain coupled | Large environment + prebuilt wheels only |
| validation-requires-source-vs-installed-boundary | active candidate | medium | Fresh upstream clone + upstream PR ref + lean source-checkout path passed; published/install-tool bootstrap path also documented as viable | Both paths can succeed, so the lesson may be boundary discipline rather than exclusivity of one path | validation-prefers-lean-runtime-paths; avoid-unnecessary-native-build-pressure | This is closer to a validation-method rule than a runtime mechanism; still needs clearer discriminators | Source checkout + no compile steps vs installed-tool path under equivalent dependency pressure |
| avoid-unnecessary-native-build-pressure | leading candidate | medium-high | Plain `uv sync` on fresh checkout triggered `ruff` Rust/native build and OOMed; `uv sync --no-dev` / lean install paths avoided that failure mode; upstream audit still flagged heavy provider/native stacks as Android risk | Some lean installs still resolve native-heavy packages and pass, so the real mechanism may be avoidable compile spikes/dev-group churn rather than “all native is bad” | validation-prefers-lean-runtime-paths | Need evidence from broader environments where compile pressure stays low | Large environment + prebuilt wheels only |

#### Parent candidate verdict rule

- If one or more child candidates survive repeated mutants, **promote the child** and keep or reject the parent.
- If the parent remains only a slogan for multiple child mechanisms, mark it **rejected as too coarse** rather than promoting it.
- If the parent eventually names a real umbrella validation pattern that survives decomposition, it can remain **umbrella doctrine**, but that bar should be annoyingly high.

---

## Rejected / suspect doctrines

| Candidate decision | Evidence count | Challenges | Status | Why rejected or suspect |
|---|---:|---:|---|---|
| browser-automation-never-works-on-android | 2 | failed | rejected | Too absolute. Later browser bridge / handoff / optional capability work proved the right lesson is optionalization and graceful degradation, not impossibility |
| remove-playwright-and-android-is-fixed | 4 | failed | rejected | Dependency audits and fresh install proofs showed Playwright was only one friction point; provider/native-heavy extras still broke the lean story |
| validation-requires-system-python | 2 | failed | rejected as stated | Both Termux system Python and a clean lean venv on a non-system interpreter path passed. Interpreter choice may still matter in some mutants, but “system Python is required” did not survive contact with reality |

---

## Evidence pool

### Branch / fix evidence
- `android-graceful-deps`
- `android-optional-playwright`
- `playwright-goblin-fix`
- `optional-deps-sweep`
- `termux-bootstrap`

### Artifact / log evidence
- `outputs/droid_upstream_dependency_audit.md`
- `outputs/lean-bootstrap-installer-pr.md`
- `outputs/pr496-body.md`
- `outputs/pr496-bare-termux-proof.log`
- `outputs/pr496-final-clean-termux-20260622-121131.log`
- `outputs/pr496-final-status.json`
- `outputs/pr494-superseded.md`
- `cp-depsurgery-install-1782086376.log`

---

## Promotion rule

Promote a candidate only when it survives multiple Android mutants, for example:

1. fresh install mutant
2. optional dependency mutant
3. browser/tooling absence mutant
4. bootstrap / bare-Termux validation mutant

If it does not survive repeated challenge, keep it candidate or mark it rejected.
