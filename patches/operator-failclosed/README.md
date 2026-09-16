# Operator plugin — fail-closed compatibility patch

**Provenance:** version-controlled snapshot of the externally-managed operator
plugin at `~/.code_puppy/plugins/operator/register_callbacks.py`.

That plugin is **Operator-Memory managed** (see its `.operator-managed` marker)
and can self-update, which means it may overwrite the fixes below on a runtime
refresh. This copy is the recovery source of truth if that happens.

## What this patch does

Hardens the operator ↔ Code Puppy boundary against API drift, per the governance
invariants (kennel `repo → decisions`, 2026-08-22):

1. **`get_current_session_name`** — monotonic shim:
   new name → `get_current_autosave_session_name` → `get_current_autosave_id`
   → `None` stub (NOT a colliding `"default"`).
2. **`get_conversation_root_id`** — import guarded (absent in older builds) →
   returns `None`.
3. **`_conversation_key()`** — returns `str | None`; **fails closed** when both
   identity sources are unavailable.
4. **`_inject_preamble()`** — no-ops (passthrough) on a falsy key: no preamble
   insert, no `_render_tasks` cache write, so no cross-partition collision.

## Rule this enforces

- Fallback-for-convenience on cosmetic/renamed APIs.
- **Fail-closed** on identity / authority / capability-bearing state.
- Missing operator context is safe; cross-contaminated context is not.

## Restore

```sh
cp patches/operator-failclosed/register_callbacks.py \
   ~/.code_puppy/plugins/operator/register_callbacks.py
```

> NOTE: the matrix these fixes were proven against is **code-puppy 0.0.568**.
> After moving to 0.0.759 the seam must be **re-validated** against the new API
> surface (fallbacks remain safe, but the proof is stale).
