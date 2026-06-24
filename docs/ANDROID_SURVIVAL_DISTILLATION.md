# Android Survival Distillation

This note distills repeated Android/Termux evidence into durable doctrine candidates.

## Evidence basis

### Branch / fix trail
- `android-graceful-deps`
- `android-optional-playwright`
- `playwright-goblin-fix`
- `optional-deps-sweep`
- `termux-bootstrap`
- lean bootstrap planner / installer work

### Artifact trail
- `outputs/droid_upstream_dependency_audit.md`
- `outputs/lean-bootstrap-installer-pr.md`
- `outputs/pr496-body.md`
- `outputs/pr496-bare-termux-proof.log`
- `outputs/pr496-final-clean-termux-20260622-121131.log`
- `outputs/pr496-final-status.json`
- `outputs/pr494-superseded.md`
- `cp-depsurgery-install-1782086376.log`

## Distilled decisions

### 1. Desktop-only dependencies must degrade gracefully

Repeated evidence shows Android pain did not come from one package. It came from
assuming desktop-ish capabilities were safe to attach in the base path. The
surviving rule is that heavy or environment-sensitive dependencies must fail
soft and stay optional when the target cannot support them.

Evidence highlights:
- Playwright had to move behind optional capability gates.
- Provider/image/fuzzy/search stacks remained install friction when core.
- Fresh Android dependency audits repeatedly showed that “Playwright is gone”
  was not enough if other native-heavy extras still rode in core.

### 2. Bootstrap must succeed on a lean Android install path

The durable lesson is not merely “document more steps.” It is that Android
installs need a separate lean bootstrap path that detects first, installs lean,
and reattaches optional capability later.

Evidence highlights:
- bootstrap planner / wizard work
- `android-termux-lean` profile
- PR 494/496 history
- fresh Android proof artifacts showing lean install succeeds where broad sync
  or heavy base dependency resolution fails

### 3. Browser capabilities are optional capabilities, not core runtime assumptions

Browser tooling is valuable, but Android survival proved it must not be treated
as a core runtime assumption. Playwright absence, missing CDP, and constrained
phone environments must leave the CLI alive and the install viable.

Evidence highlights:
- Playwright optionalization work across multiple branches
- browser import guards / unavailable messages
- Android proof logs showing CLI/import success with browser extras absent

### 4. Missing tooling should trigger degradation, not startup failure

The durable rule is broader than browser tooling. Missing rg, missing Playwright,
missing optional native modules, or unsupported helpers should produce a precise
unavailable/degraded mode, not kill startup.

Evidence highlights:
- graceful dependency work
- system `rg` vs PyPI `ripgrep` split
- import guards for optional modules
- proof logs showing `code-puppy --help` and package import still succeed while
  optional native helpers remain absent

## Stored decision ids

The following decision ids were created from this distillation pass:
- `android-desktop-deps-degrade-gracefully`
- `android-bootstrap-uses-lean-install-path`
- `android-browser-capabilities-are-optional`
- `android-missing-tooling-triggers-degradation`

## Next question

Do these Android decisions start producing doctrine warnings and receipts when a
future change tries to pull browser/native-heavy assumptions back into the base
path?
