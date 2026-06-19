"""Tests for read-only AuthorityGrant registry validation."""

from __future__ import annotations

import json

from code_puppy.plugins.project_runtime import authority_validator, commands, store


def _use_tmp_state(tmp_path, monkeypatch):
    state_file = tmp_path / "project_runs.json"
    monkeypatch.setattr(store, "STATE_FILE", str(state_file))
    return state_file


def _load_raw(state_file):
    return json.loads(state_file.read_text(encoding="utf-8"))


def _save_raw(state_file, state):
    state_file.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def test_authority_validate_empty_registry_passes_read_only(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    before = state_file.read_text(encoding="utf-8") if state_file.exists() else ""

    output = commands.dispatch(["authority", "validate"])

    assert output.startswith("Project Authority Validation")
    assert "status    : PASS" in output
    assert "grants    : 0" in output
    assert "mutates   : no" in output
    assert "authorizes: no" in output
    assert "leases    : no" in output
    assert "executes  : no" in output
    assert "Violations:\n- (none)" in output
    after = state_file.read_text(encoding="utf-8") if state_file.exists() else ""
    assert after == before


def test_authority_validate_well_formed_grant_passes(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(
        project="Code Puppy",
        objective="Eligible work",
        run_id="run-eligible",
        status="ready",
    )
    state = _load_raw(state_file)
    state["authority_grants"] = {
        "grant-runtime-step": {
            "grant_id": "grant-runtime-step",
            "subject_identity": "unassigned_agent",
            "allowed_action_scope": "project_run.execute_bounded_step",
            "allowed_capability_scope": "project_runtime.step",
            "boundary": "project_run",
            "issuer": "operator",
            "issued_at": "2026-01-01T00:00:00+00:00",
            "expires_at": "2099-01-01T00:00:00+00:00",
            "run_id": "run-eligible",
            "reason": "test grant",
            "precedent_id": "PRECEDENT-006",
        }
    }
    _save_raw(state_file, state)
    before = state_file.read_text(encoding="utf-8")

    report = authority_validator.validate_authority()
    output = authority_validator.format_report(report)

    assert report.passed
    assert "status    : PASS" in output
    assert "grants    : 1" in output
    assert "Violations:\n- (none)" in output
    assert state_file.read_text(encoding="utf-8") == before


def test_authority_validate_reports_registry_violations_read_only(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    store.create_run(
        project="Code Puppy",
        objective="Eligible work",
        run_id="run-eligible",
        status="ready",
    )
    state = _load_raw(state_file)
    state["authority_grants"] = {
        "grant-a": {
            "grant_id": "dup-grant",
            "subject_identity": "bad identity",
            "allowed_action_scope": "project_run.*",
            "allowed_capability_scope": "",
            "boundary": "global",
            "issuer": "",
            "issued_at": "not-a-time",
            "run_id": "missing-run",
            "project_id": "Code Puppy",
            "precedent_id": "PRECEDENT-NOPE",
        },
        "grant-b": {
            "grant_id": "dup-grant",
            "subject_identity": "agent-1",
            "allowed_action_scope": "project_run.execute_bounded_step",
            "allowed_capability_scope": "project_runtime.step",
            "boundary": "project_run",
            "issuer": "operator",
            "issued_at": "2026-01-01T00:00:00+00:00",
            "expires_at": "2025-01-01T00:00:00+00:00",
            "revoked_at": "2025-12-31T00:00:00+00:00",
            "run_id": "run-eligible",
        },
        "not-structured": "trash",
    }
    _save_raw(state_file, state)
    before = state_file.read_text(encoding="utf-8")

    output = commands.dispatch(["authority", "validate"])

    assert "status    : FAIL" in output
    assert "grants    : 3" in output
    assert "Every AuthorityGrant must be a structured record." in output
    assert "AuthorityGrant grant_id must match registry key." in output
    assert "AuthorityGrant grant_id values must be unique." in output
    assert "AuthorityGrant subject_identity must be a stable identity token." in output
    assert "AuthorityGrant scopes must be exact normalized names." in output
    assert "AuthorityGrant scopes are required." in output
    assert "AuthorityGrant boundary must be supported." in output
    assert "AuthorityGrant must name exactly one run or project boundary." in output
    assert "AuthorityGrant issuer is required." in output
    assert "AuthorityGrant issued_at timestamp must be parseable." in output
    assert "AuthorityGrant expires_at must be after issued_at." in output
    assert "AuthorityGrant revoked_at cannot be before issued_at." in output
    assert "AuthorityGrant precedent_id must reference a known precedent." in output
    assert state_file.read_text(encoding="utf-8") == before


def test_authority_validate_rejects_arguments(tmp_path, monkeypatch):
    _use_tmp_state(tmp_path, monkeypatch)

    try:
        commands.dispatch(["authority", "validate", "--fix"])
    except ValueError as exc:
        assert (
            "authority usage: /project authority grants | grant-draft | "
            "validate | grant-create-plan" in str(exc)
        )
    else:  # pragma: no cover - defensive
        raise AssertionError("expected authority validate command to reject args")
