# 0.0.759 Migration - Build-Host Qualification Checklist

Candidate: `puppy-stable` @ `2bc80060` (tag `rebase-0.0.759-complete`).
Rollback anchor: tag `pre-0.0.759-switch` @ `e9ab29ab`.
Remote `fork/puppy-stable` is UNCHANGED at `59acbabe` (0.0.759) - nothing published yet.

> **Rule:** the rebase earned only history/syntax/authority-boundary proof.
> Dependency, import, and behavioral proof are EARNED HERE. "Rebase done"
> is not "release-qualified." Run steps in order; stop at first red.

## Step 0 - get the candidate on the build host AND PROVE THE SHA

The candidate is published to the NON-STABLE review branch
`candidate/0.0.759` on the `fork` remote (github kvandre12-commits).
The stable pointer `fork/puppy-stable` remains at `59acbabe` (bare 0.0.759).

> **DO NOT `checkout puppy-stable`** - that lands you on `59acbabe`, the bare
> upstream WITHOUT the 92 authored commits. You would qualify the wrong
> artifact. Target `candidate/0.0.759` (or the tag) explicitly.

```sh
cd ~/code_puppy
git fetch --all --tags
git checkout -B qualify-0.0.759 fork/candidate/0.0.759   # or: git checkout rebase-0.0.759-complete
git status                                                # MUST be clean
git rev-parse HEAD                                        # MUST print 1487ce96...
```

If `git rev-parse HEAD` is NOT `1487ce96...`, STOP - you are not on the
candidate. Do not install or run anything until the SHA matches.

> **Do not pull / rebase / update the candidate before qualifying it.**
> `1487ce96` is the artifact under test. Modifying it first means you are
> qualifying something else.

## Step 1 - dependency resolution (regenerate the lock; Termux could not)

```sh
uv sync --all-extras          # resolves 0.0.759 harness + browser/fuzzy/images/search
uv lock                       # regenerate uv.lock (was taken from 759 as-is)
git diff --stat uv.lock       # expect churn; review it's sane
```
Red here = pyproject composition problem. Do not proceed.

## Step 2 - imports (the proof Termux could not give)

```sh
uv run python -c "import code_puppy; import code_puppy.config, code_puppy.claude_cache_client, code_puppy.model_factory, code_puppy.agents.base_agent, code_puppy.tools.subagent_invocation, code_puppy.token_usage; print('core imports OK')"
uv run python -c "import code_puppy.plugins.puppy_kennel.register_callbacks, code_puppy.plugins.droid_viewer.register_callbacks, code_puppy.plugins.bridge_grants.register_callbacks, code_puppy.plugins.ollama.register_callbacks; print('plugin imports OK')"
```
Red here = an orphan/contract mismatch survived. (We removed two known
orphans: context_indicator plugin + claude cache test. Watch for more.)

## Step 3 - targeted boundary tests (the authority surfaces first)

```sh
uv run pytest tests/ -k "claude_cache or oauth or transport" -q     # OAuth/transport boundary
uv run pytest tests/ -k "prompt or system_prompt or runtime" -q      # prompt assembly (759 stack)
uv run pytest tests/plugins/test_puppy_kennel -q                     # kennel injection
uv run pytest tests/ -k "auto_save or busy_port or http_utils" -q    # our re-applied hunks
```

## Step 4 - full suite

```sh
uv run pytest -q
```

## Step 5 - inspection

```sh
git status
git log --oneline 59acbabe..HEAD | wc -l     # expect ~91
git grep -n '<<<<<<<' || echo "no markers"
```

## Publish vs Bless - TWO SEPARATE AUTHORITY DECISIONS

These are NOT the same call. Do not conflate.

1. **Publish for inspection** (optional, safe): push candidate to a
   review branch, e.g. `git push fork rebase-0.0.759-complete:candidate/0.0.759`.
   This lets others inspect WITHOUT declaring it stable.

2. **Bless as stable runtime** (only after Steps 1-5 all green + operator go):
   `git push --force-with-lease fork puppy-stable`.
   Force-push and stable-blessing are the same command here only because
   `fork/puppy-stable` IS the stable pointer - which is exactly why it waits
   for full behavioral proof.

## Known post-migration follow-ups (isolated, non-blocking)

1. `uv.lock` regenerated in Step 1 (was carried from 759 as-is).
2. README lost cross-links to `docs/AGENT_POWER.md` + `docs/AGENT_ORG_CHART.md`
   (the doc FILES are preserved on disk - just re-add the links).
3. 3-breakpoint Anthropic `cache_control` injection was dropped from
   `claude_cache_client.py` to protect the transport boundary. Clean re-add
   later as an isolated enhancement if wanted - do NOT reintroduce it by
   reverting to the old file (that would re-cross the boundary).
