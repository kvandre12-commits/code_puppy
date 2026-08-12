# Phone-Port Workspace Map

_Last updated: 2026-06-26_

## Purpose

This is the human-readable map for the Android/Termux workspace around this repo.

It exists because the directory layout in `/data/data/com.termux/files/home/` can
look like random mutant sprawl when, in reality, much of it came from trying to
get upstream Code Puppy working on the phone.

Treat the sibling directories as **phone-port evidence layers** first and as
random junk only after verifying they are no longer needed.

## Anchor point

Current repo:

- `/data/data/com.termux/files/home/code_puppy_backup_20260617`

This checkout is a **Code Puppy fork / working backup checkout** with a large
DroidPuppy Android overlay embedded inside it.

## Mental model

There are four main species in this yard:

1. **Primary repos** — real projects you may actively work in
2. **Phone-port clones/worktrees** — created while validating upstream Code Puppy
   on Android/Termux
3. **Temporary env/proof dirs** — fresh installs, venvs, audit runs, and logs
4. **Artifact piles** — screenshots, reports, manifests, and test evidence

## Top-level sibling map

### Primary repos

| Path | What it is | Notes |
|---|---|---|
| `~/code_puppy/` | Main Code Puppy checkout | Looks like the canonical local Code Puppy repo in this workspace |
| `~/code_puppy_backup_20260617/` | Backup / working DroidPuppy-heavy checkout | Current repo for this session |
| `~/SharpEdge-System/` | SharpEdge trading / cockpit / backend repo | Owns trading truth, not Code Puppy |
| `~/SharpEdge-Android/` | Native Android viewer/app repo | Primary SharpEdge Android UI line |
| `~/SharpEdge-Robinhood-Bridge/` | Robinhood bridge repo | Separate broker-side boundary |
| `~/Vanlock/` | Separate project | Not related to Code Puppy phone-port work |
| `~/TENSION-MODEL/` | Separate project/data area | Not part of Code Puppy port debugging |
| `~/worldseed-review-20260621-205312/` | Separate repo | Appears intentional, not junk |
| `~/meat_report/` | Tiny standalone project | Separate from Code Puppy work |

### Code Puppy phone-port clones / worktrees

These were likely created to test upstream, specific PR states, or trimmed install
paths on Android/Termux.

| Path | Likely purpose | Important note |
|---|---|---|
| `~/code_puppy_pr483/` | PR/worktree validation | `.git` points at `~/code_puppy/.git/worktrees/...` |
| `~/code_puppy_pr483_followup/` | follow-up worktree | `.git` points at `~/code_puppy_backup_20260617/.git/worktrees/...` |
| `~/code_puppy_pr483_minimal/` | reduced/minimal variant | Inspect before deletion |
| `~/code_puppy_pr494_fix/` | fix-specific worktree | Worktree-flavored; do not blindly delete |
| `~/code_puppy_optional_deps/` | optional dependency experiment | Worktree-flavored |
| `~/code_puppy_playwright_tiny/` | lean Playwright / optional browser experiment | Worktree-flavored |
| `~/code_puppy_test_20260622-102330/` | dated test checkout | Likely proof run / disposable clone |
| `~/code_puppy_test_current_20260622-103044/` | dated current-state proof checkout | Has tiny proof marker files |
| `~/code_puppy_upstream_pr496_20260622-103342/` | upstream PR ref proof checkout | Likely validation evidence |
| `~/cp-fresh-test/` | fresh install/test checkout | `install.log` confirms package install testing |
| `~/cp-clean-audit-1782080016/` | clean-environment audit checkout | Probably disposable once lessons are captured |
| `~/cp496-proof-1782122760/` | proof checkout for PR/validation path | Likely evidence directory |

### Temporary env / support dirs

| Path | What it is | Notes |
|---|---|---|
| `~/cp-clean-audit-1782080016-venv/` | venv | Safe-looking env sludge, not source |
| `~/cp-depsurgery-venv/` | venv | dependency surgery env |
| `~/cp-depsurgery-venv-1782086376/` | venv | dated env clone |
| `~/cp-wiz-test-venv/` | venv | likely bootstrap/wizard testing |
| `~/testenv/` | generic env | inspect only if still in use |
| `~/tmp/` | scratch area | contains APK dumps, screenshots, install logs |
| `~/mike_test_fresh_home_20260624-102434/` | isolated fresh-home test area | likely evidence of fresh-home validation |
| `~/mike_test_proxy_*` | proxy test dirs | test evidence, not source design |
| `~/droidpuppy_branch_proxy_20260624-094055/` | branch proxy test dir | test evidence |

### Artifacts / evidence piles

| Path | What it is | Notes |
|---|---|---|
| `~/code_puppy_backup_20260617/outputs/` | screenshots, manifests, reports, logs | Evidence-rich, not core source |
| `~/code_puppy_backup_20260617/docs/FAILED_*` etc. | test run notes and result ledgers | Useful for archaeology |
| `~/outputs/` | shared top-level outputs | inspect before cleanup |

## Current repo map

Inside `~/code_puppy_backup_20260617/` the important zones are:

| Path | Role |
|---|---|
| `code_puppy/` | main Code Puppy runtime |
| `DroidPuppy/` | Android overlay / contracts / orchestra prototype |
| `tests/` | regression coverage |
| `docs/` | architecture docs + validation ledgers |
| `outputs/` | generated artifacts / screenshots / manifests / reports |
| `scripts/` | install/onboarding helpers |

## Known weirdness

### 1. Backup checkout identity is real

This repo is itself a backup-named checkout:

- `code_puppy_backup_20260617`

So future confusion about "why is this not just `code_puppy/`?" is expected.

### 2. Some sibling clones are real git worktrees

At least some `code_puppy_*` siblings are not dumb copies. Their `.git` files
point to parent-repo worktree metadata.

Examples:

- `~/code_puppy_pr483/.git` -> `~/code_puppy/.git/worktrees/code_puppy_pr483`
- `~/code_puppy_pr483_followup/.git` -> `~/code_puppy_backup_20260617/.git/worktrees/code_puppy_pr483_followup`
- `~/code_puppy_pr494_fix/.git` -> `~/code_puppy_backup_20260617/.git/worktrees/code_puppy_pr494_fix`
- `~/code_puppy_optional_deps/.git` -> `~/code_puppy_backup_20260617/.git/worktrees/code_puppy_optional_deps`
- `~/code_puppy_playwright_tiny/.git` -> `~/code_puppy/.git/worktrees/code_puppy_playwright_tiny`

So if cleaning up later, prefer proper `git worktree` cleanup from the owning
repo rather than deleting folders like a raccoon with root access.

### 3. One malformed directory was observed

In `~/SharpEdge-Android/` there is a suspicious path resembling:

- `{app_contracts,docs,app`

This looks like an accidental brace-expansion / shell mishap, not an intentional
repo structure decision.

## Cleanup rules of thumb

### Usually keep

- primary repos
- worktrees still tied to meaningful experiments
- proof dirs whose findings are not yet distilled into docs

### Usually safe to remove later

- dead venvs
- transient `tmp/` screenshots and APK dumps
- stale fresh-test checkouts once the lesson is documented
- redundant artifact logs after durable conclusions are captured elsewhere

### Do not assume

- that every `code_puppy_*` sibling is junk
- that backup naming means unimportant
- that output-heavy directories are design source

## Why this map exists

Short version:

> Most of the apparent workspace sprawl came from trying to get upstream Code
> Puppy working on the phone, especially through Android/Termux install,
> dependency, fresh-home, and proof-of-path experiments.

That is the lens future-us should use before cleaning or reorganizing anything.
