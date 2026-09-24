# MAP.md — code_puppy orientation map

> Living map so we never re-discover architecture we figured out months ago.
> Generated 2026-09-24 from direct detection (launcher resolution + git evidence).
> Update this file whenever the canonical branch, launcher, or repo layout changes.

---

## 1. Repository & remote map

**This repo (`code_puppy`)** — checkout at `~/code_puppy_primary_candidate`

| remote | URL | meaning |
|--------|-----|---------|
| `origin` | https://github.com/kvandre12-commits/code_puppy.git | **YOURS** — the fork. Push all work here. |
| `upstream` | https://github.com/mpfaffenberger/code_puppy.git | the original public project (reference only; we do not need to merge into it) |

Remotes were renamed 2026-09-24 so `origin` = yours (was previously named `fork`;
`upstream` was previously misleadingly named `origin`).

**Related repos in the estate** (separate git repos):
- `~/SharpEdge-System` — trading system (NERV, Alpha Swarm paper pilots, live cockpit, confluence-zone engine). Remote `origin` = kvandre12-commits/SharpEdge-System.
- `~/sharpedge_spy` — live SPY/WMT/AMZN options board + alerts + Gemini "Copilot" sidecar (port 8781).
- `~/whetstone`, `~/whetstone-web` — writing tool (research scout + Socratic coach).
- `~/oss/pykrx` — fork for OSS give-back (PR #298 upstream).

---

## 2. Canonical runnable checkout / branch / HEAD  (VERIFIED)

- **Checkout:** `~/code_puppy_primary_candidate`
- **Branch:** `feature/intelligence-registry`
- **HEAD:** `851794c0` — "Establish process-owned intelligence registry"
- **Version:** `0.0.817`  (`git describe` = `v0.0.817-9-g851794c0` → 0.0.817 base + 9 commits)
- **Worktree at time of writing:** CLEAN
- **Import mode:** EDITABLE — the launcher imports `code_puppy` directly from this checkout
  (`.../code_puppy_primary_candidate/code_puppy/__init__.py`), so edits to source take effect
  immediately with no reinstall.

Lineage: `feature/intelligence-registry` = the **"Mike-main" 0.0.817 base** (`e862b67`) **plus**
the intelligence-registry feature (provider quota/credit/retry observations).

---

## 3. Active launcher & environment  (VERIFIED)

Primary command: **`code-puppy`**
```
~/.local/bin/code-puppy
  -> ~/code_puppy_primary_candidate/.venv-runtime-nodev/bin/code-puppy
  shebang python: ~/code_puppy_primary_candidate/.venv-runtime-nodev/bin/python
  entrypoint: code_puppy.main:main_entry
```

Other launchers present in `~/.local/bin` (know what each is so you don't confuse them):

| launcher | target | notes |
|----------|--------|-------|
| `code-puppy` | primary_candidate `.venv-runtime-nodev` (editable) | **canonical dev/runtime** (feature/intelligence-registry) |
| `code-puppy-clean` | pipx venv, site-packages **v0.0.720** | **stable pinned fallback** (NOT a checkout) — use if the dev line breaks |
| `code-puppy-primary-candidate` | primary_candidate `.venv` (dev venv w/ pytest 9.1.1) | dev venv used for tests |
| `code-puppy-primary-nodev` | same as `code-puppy` | runtime venv (no dev deps) |
| `code-puppy-bootstrap`, `pup` | uv tools install | bootstrap/uv path |
| `code-puppy-clean` / `pup-clean` | pipx v0.0.720 | clean fallback |
| `droid-puppy` | `~/droid_operator_runtime/.venv` | separate droid operator runtime |

Two venvs in this checkout:
- `.venv` — dev venv, **has pytest 9.1.1** (use for tests)
- `.venv-runtime-nodev` — lean runtime venv, **no pytest** (used by the `code-puppy` launcher)

---

## 4. Important branches & purpose
(Summarized from each branch's latest commit; all on `origin` = your fork.)

**Runtime / main lines**
- `feature/intelligence-registry` — **CANONICAL runtime.** Process-owned intelligence registry: provider quota/credit/retry observations (the machinery for knowing when a model is credit-gated or rate-limited).
- `main` (local) = `e862b67` — **"Mike-main" / 0.0.817 base line.** Preserved. NOTE: this is a DIFFERENT history from `origin/main`.
- `backup/main-20260924` = `e862b67` — safety snapshot of local `main` pushed 2026-09-24.
- `origin/main` = `b75b2d0f` (2026-08-23) — the fork's own main line ("ci: exact-SHA candidate qualification"). **Different history from local main** (see warning below).
- `puppy-stable`, `candidate/0.0.759`, `pristine/code-puppy-v0.0.569` — pinned/stable reference snapshots.

**Lean / Android (Termux) customizations** — the "lean thing"
- `feature/lean-bootstrap-installer` — native Android bootstrap flow.
- `lean-droid-installs` — make provider SDKs optional for lean installs.
- `upstream-lean-provider-extras` — mark Android-incompatible extras optional.
- `android-graceful-deps` — defer Playwright import until browser init.
- `droidpuppy` — Android onboarding + lean packaging guards.
- `android-share-packet` — operator-centered docs.

**Feature / plugin work**
- `private-operator-channel-mvp-2` — private operator channel plugin.

**Upstream contribution branches (optional; PRs to mpfaffenberger)**
- `fix/child-agent-cache-prefix` — PR #937 (MERGEABLE/CLEAN as of 2026-09-24).
- `fix/exhaustive-grep-pagination` (#905), `fix/prefer-environment-ripgrep` (#819),
  `feat/plugin-tool-surface-filter` (#817), `fix/config-hot-path-cache` (#786) — currently CONFLICTING with upstream (stale); rescue one at a time only if still valuable.
- `fix/issue-438-threadsafe-futures` — MERGED upstream (#885).

---

## 5. Exact commands (run / update / test / backup / rollback)

**Run**
```sh
code-puppy                 # canonical (feature/intelligence-registry, editable)
code-puppy-clean           # stable v0.0.720 fallback if the dev line is broken
```

**Update / sync from your fork** (editable — no reinstall needed for source changes)
```sh
cd ~/code_puppy_primary_candidate
git fetch origin
git status -sb                         # see where the current branch stands
# to pull latest on the current branch (fast-forward only, safe):
git pull --ff-only origin feature/intelligence-registry
```

**Test** (use the dev venv, which has pytest)
```sh
cd ~/code_puppy_primary_candidate
.venv/bin/python -m pytest -q          # full suite (pytest 9.1.1, cov configured)
.venv/bin/python -m pytest tests/test_intelligence_registry.py -q   # targeted
ruff check .                           # lint
```

**Backup (push work to your fork)**
```sh
cd ~/code_puppy_primary_candidate
git push origin feature/intelligence-registry              # back up the canonical branch
# dated safety snapshot of any branch, non-destructive:
git push origin HEAD:refs/heads/backup/<name>-$(date +%Y%m%d)
```

**Rollback**
```sh
# fastest: just run the pinned stable build
code-puppy-clean
# or check out a preserved line in the dev checkout:
cd ~/code_puppy_primary_candidate
git checkout backup/main-20260924      # the 0.0.817 "Mike-main" base
git checkout <sha>                     # any known-good commit
```

---

## 6. WARNING — divergent main histories

`origin/main` (fork) and `backup/main-20260924` (= local `main` = the 0.0.817 "Mike-main" base)
are **DIFFERENT histories**, not two copies of one line:

- `origin/main` = `b75b2d0f`
- `backup/main-20260924` = local `main` = `e862b67`
- divergence: **80 commits only on `origin/main`, 954 only on the backup/local-main line**

Do NOT assume they are interchangeable, and do NOT force-move `origin/main` onto the local
main line (or vice-versa) without a deliberate, reviewed decision. Both are preserved on the
fork today; picking a single unified `main` is a future decision, not an accident to trip into.
