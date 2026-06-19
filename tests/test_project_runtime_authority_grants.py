"""Tests for read-only Project OS authority grant reporting."""

from __future__ import annotations

import json

from code_puppy.plugins.project_runtime import commands, store


def _use_tmp_state(tmp_path, monkeypatch):
    state_file = tmp_path / "project_runs.json"
    monkeypatch.setattr(store, "STATE_FILE", str(state_file))
    return state_file


def _save_raw(state_file, state):
    state_file.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def test_authority_grants_lists_empty_store_read_only(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    before = state_file.read_text(encoding="utf-8") if state_file.exists() else ""

    output = commands.dispatch(["authority", "grants"])

    assert output.startswith("Project Authority Grants")
    assert "mutates   : no" in output
    assert "authorizes: no" in output
    assert "leases    : no" in output
    assert "executes  : no" in output
    assert "Grants:\n- (none)" in output
    after = state_file.read_text(encoding="utf-8") if state_file.exists() else ""
    assert after == before


def test_authority_grants_lists_configured_grants_read_only(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _save_raw(
        state_file,
        {
            "version": 1,
            "runs": {},
            "events": {},
            "authority_grants": {
                "grant-runtime-step": {
                    "grant_id": "grant-runtime-step",
                    "subject_identity": "unassigned_agent",
                    "allowed_action_scope": "project_run.execute_bounded_step",
                    "allowed_capability_scope": "project_runtime.step",
                    "boundary": "project_run",
                    "issuer": "operator",
                    "issued_at": "2026-01-01T00:00:00+00:00",
                    "expires_at": "2026-01-01T00:15:00+00:00",
                    "run_id": "run-eligible",
                    "reason": "test grant",
                    "precedent_id": "PRECEDENT-006",
                }
            },
        },
    )
    before = state_file.read_text(encoding="utf-8")

    output = commands.dispatch(["authority", "grants"])

    assert "grant_id                : grant-runtime-step" in output
    assert "subject_identity        : unassigned_agent" in output
    assert "allowed_action_scope    : project_run.execute_bounded_step" in output
    assert "allowed_capability_scope: project_runtime.step" in output
    assert "boundary                : project_run" in output
    assert "run_id                  : run-eligible" in output
    assert "issuer                  : operator" in output
    assert "reason                  : test grant" in output
    assert "precedent_id            : PRECEDENT-006" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_authority_grants_rejects_other_authority_commands(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)

    try:
        commands.dispatch(["authority", "grant", "create"])
    except ValueError as exc:
        assert (
            "authority usage: /project authority grants | grant-draft | "
            "validate | grant-create-plan" in str(exc)
        )
    else:  # pragma: no cover - defensive
        raise AssertionError("expected unsupported authority command to fail")
