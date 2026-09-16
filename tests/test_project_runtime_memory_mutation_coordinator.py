"""Proof that governed memory mutation refuses without an atomicity seam."""

from __future__ import annotations

import json

from code_puppy.plugins.project_runtime import (
    commands,
    memory_mutation_coordinator,
    store,
)

RUN_ID = "run-memory-promote-cli"
GRANT_ID = f"grant:{RUN_ID}:{memory_mutation_coordinator.MEMORY_PROMOTE_ACTION_SCOPE}"
LEASE_ID = f"lease:{RUN_ID}:{memory_mutation_coordinator.MEMORY_PROMOTE_ACTION_SCOPE}"


def _use_tmp_state(tmp_path, monkeypatch):
    state_file = tmp_path / "project_runs.json"
    monkeypatch.setattr(store, "STATE_FILE", str(state_file))
    return state_file


def _load_raw(state_file):
    return json.loads(state_file.read_text(encoding="utf-8"))


def _create_ready_run():
    return commands.dispatch(
        [
            "run",
            "create",
            RUN_ID,
            "--project",
            "Code Puppy",
            "--objective",
            "Prove governed memory mutation seam",
            "--status",
            "ready",
        ]
    )


def _grant_and_issue_memory_promote_lease():
    commands.dispatch(
        [
            "authority",
            "grant-create",
            "--effect",
            "memory-promote",
            "--confirm",
            GRANT_ID,
        ]
    )
    return commands.dispatch(
        [
            "run",
            "lease-issue",
            "--effect",
            "memory-promote",
            "--confirm",
            LEASE_ID,
        ]
    )


def _execute_promote(**overrides: str):
    args = [
        "run",
        "execute-memory-promote",
        "--confirm",
        overrides.get("confirm", LEASE_ID),
        "--source-evidence",
        overrides.get("source_evidence", "quarantine drawer 123"),
        "--reason",
        overrides.get("reason", "promote stable Project OS decision"),
        "--after",
        overrides.get("after", "durable decision object"),
    ]
    return commands.dispatch(args)


def test_memory_promote_refuses_when_atomicity_is_unavailable(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    assert "Created Project Run" in _create_ready_run()
    draft = commands.dispatch(
        ["authority", "grant-draft", "--effect", "memory-promote"]
    )
    assert f"grant_id               : {GRANT_ID}" in draft
    assert "allowed_action_scope   : memory.promote" in draft
    assert "allowed_capability     : memory.write.project_context" in draft
    assert (
        "issued                      : yes" in _grant_and_issue_memory_promote_lease()
    )

    before = state_file.read_text(encoding="utf-8")
    result = _execute_promote()

    assert "executed                    : no" in result
    assert "atomicity unavailable for split governance/knowledge stores" in result
    assert "consumes_lease              : no" in result
    assert "mutates_project_os          : no" in result
    assert "mutates_kennel              : no" in result
    assert "creates_audit_event         : no" in result
    assert state_file.read_text(encoding="utf-8") == before

    state = _load_raw(state_file)
    lease = state["leases"][LEASE_ID]
    assert lease["consumed_at"] == ""
    assert lease["consumed_event_id"] == ""
    assert not any(
        event["event_type"] == "memory_mutation_effect_executed"
        for event in state["events"].values()
    )


def test_memory_promote_missing_evidence_refuses_without_consuming_lease(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run()
    _grant_and_issue_memory_promote_lease()
    before = state_file.read_text(encoding="utf-8")

    result = _execute_promote(source_evidence="   ")

    assert "executed                    : no" in result
    assert "memory mutation blocked by missing evidence" in result
    assert "source evidence missing" in result
    assert "consumes_lease              : no" in result
    assert "mutates_kennel              : no" in result
    assert state_file.read_text(encoding="utf-8") == before


def test_memory_promote_consumed_lease_refuses_without_new_state_change(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run()
    _grant_and_issue_memory_promote_lease()
    commands.dispatch(
        [
            "run",
            "execute-memory-promote",
            "--confirm",
            LEASE_ID,
            "--source-evidence",
            "quarantine drawer 123",
            "--reason",
            "promote stable Project OS decision",
            "--after",
            "durable decision object",
        ]
    )
    # The conservative refusal above does not consume the lease, so consume it
    # through the existing lease helper to prove consumed leases are rejected.
    from code_puppy.plugins.project_runtime import lease_store

    lease_store.consume_lease_for_effect(
        lease_store.get_lease(LEASE_ID),
        event_type="noop_executed",
        payload_summary="test consumed lease",
    )
    before = state_file.read_text(encoding="utf-8")

    result = _execute_promote()

    assert "executed                    : no" in result
    assert "lease already consumed" in result
    assert "mutates_kennel              : no" in result
    assert state_file.read_text(encoding="utf-8") == before
