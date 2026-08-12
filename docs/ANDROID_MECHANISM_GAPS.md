# Android Mechanism Gaps

This note tracks Android lessons that already have **evidence/results** but do **not yet** have an isolated mechanism.

Use it to prevent symptom descriptions from being promoted into doctrine.

For the canonical current posture of Android candidates, defer to
`docs/ANDROID_CANDIDATE_DECISIONS.md`.

## Known result fragments already in hand

These are not complete mutant matrices, but they are real observations already collected:

| Observation | Current result |
|---|---|
| Fresh upstream clone | pass |
| Upstream PR ref only | pass |
| System Python path | pass |
| Base Termux PATH | pass |
| Missing `ripgrep` | graceful degradation |
| Missing Playwright | graceful degradation after patch |
| Long-lived dev environment | mixed |
| Active development branch | mixed |
| ADB/CDP browser control | still unstable |
| Plain `uv sync` on Android source checkout | noisy / failure-prone |
| `uv sync --no-dev` lean runtime path | viable |

---

## Highest-value mechanism gaps

| Candidate lesson | Evidence strength | Suspected mechanisms | Why not doctrine yet |
|---|---|---|---|
| validation-requires-bare-termux | high | PATH contamination, interpreter selection, venv leakage, dev-group pressure, source-vs-installed path differences | “Bare Termux” is a symptom slogan, not an isolated cause |
| path-assumptions-are-fragile | medium | shim ordering, PATH shadowing, system-vs-project tool precedence | Could be broader than Android; mechanism still fuzzy |
| installers-must-assume-absence | medium-high | missing build chain, missing system packages, capability detachment, optional extra isolation | Overlaps several stronger promoted doctrines; needs sharper boundary |
| capabilities-over-dependencies | medium | capability registration boundaries, lazy imports, runtime detection, optional extras separation | Strong abstraction, but still too abstract without a dominant mechanism |
| android-native-first | medium | Termux package reality, Android permission/storage model, mobile runtime constraints | Risks becoming branding instead of mechanism-aware doctrine |
| avoid-unnecessary-native-build-pressure | medium-high | Rust compile pressure, dev-group expansion, unnecessary native build spikes, oversized dependency graph during validation | Stronger mechanism candidate than generic “lean is better,” but still needs more mutants to beat its competitor |
| ADB/CDP instability is an Android property | low | device setup, adb availability, port forwarding, browser debug config, transport state | Very likely false as stated; instability may belong to setup path, not platform essence |

---

## Better questions than the slogans

### Instead of
- bare Termux is required

### Ask
- Does validation only pass when PATH is clean?
- Does validation only pass with system Python?
- Does validation only pass without dev sync pressure?
- Does source-checkout validation fail where installed-tool validation passes?
- Is the real doctrine about environment isolation rather than bare Termux?

### Instead of
- Android browser automation is unstable

### Ask
- Is the instability from missing Playwright?
- from missing CDP/adb setup?
- from browser debug transport state?
- from capability registration assumptions?

---

## What is already mechanism-closer?

These look stronger because they already explain multiple failures with one mechanism family:

- optional browser capability
- graceful degradation when dependencies are absent
- lean bootstrap path before optional reattachment
- missing tooling should not kill startup

That is why they were promoted and the mechanism-gap candidates were not.

---

## Recommended next experiment

Focus first on:

- `validation-requires-bare-termux`
- head-to-head comparison in `docs/ANDROID_HEAD_TO_HEAD_MECHANISMS.md`

Likely decomposition candidates:

- validation-requires-clean-path-ordering
- validation-requires-no-venv-contamination
- validation-prefers-lean-runtime-paths
- avoid-unnecessary-native-build-pressure

Already falsified as stated:

- validation-requires-system-python

If one of those survives the mutant matrix better than the parent slogan, promote the child and reject the parent.
