"""End-to-end command proof for governed memory recall."""

from __future__ import annotations

import json

from code_puppy.plugins.project_runtime import commands, memory_recall_execution, store

RUN_ID = "run-memory-recall-cli"
GRANT_ID = f"grant:{RUN_ID}:{memory_recall_execution.MEMORY_RECALL_ACTION_SCOPE}"
LEASE_ID = f"lease:{RUN_ID}:{memory_recall_execution.MEMORY_RECALL_ACTION_SCOPE}"


def _use_tmp_state(tmp_path, monkeypatch):
    state_file = tmp_path / "project_runs.json"
    monkeypatch.setattr(store, "STATE_FILE", str(state_file))
    return state_file


def _load_raw(state_file):
    return json.loads(state_file.read_text(encoding="utf-8"))


def _events_by_type(state, event_type: str):
    return [
        event for event in state["events"].values() if event["event_type"] == event_type
    ]


def _create_ready_run():
    return commands.dispatch(
        [
            "run",
            "create",
            RUN_ID,
            "--project",
            "Code Puppy",
            "--objective",
            "Prove governed memory recall",
            "--status",
            "ready",
        ]
    )


def test_memory_recall_command_uses_same_authority_lease_audit_path(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    searches: list[tuple[str, str, int]] = []
    hits = (
        memory_recall_execution.MemoryRecallHit(
            drawer_id=101,
            role="note",
            ts="2026-01-01T00:00:00+00:00",
            content="Project OS memory recall should be governed by leases.",
        ),
    )

    def fake_searcher(query: str, wing: str, limit: int):
        searches.append((query, wing, limit))
        return hits

    monkeypatch.setattr(memory_recall_execution, "_default_searcher", fake_searcher)

    assert "Created Project Run" in _create_ready_run()
    draft = commands.dispatch(["authority", "grant-draft", "--effect", "memory-recall"])
    assert f"grant_id               : {GRANT_ID}" in draft
    assert "allowed_action_scope   : memory.recall" in draft
    assert "allowed_capability     : memory.read.project_context" in draft

    grant = commands.dispatch(
        [
            "authority",
            "grant-create",
            "--effect",
            "memory-recall",
            "--confirm",
            GRANT_ID,
        ]
    )
    assert "created                     : yes" in grant
    assert "executes                    : no" in grant

    check = commands.dispatch(["run", "authority-check", "--effect", "memory-recall"])
    assert "lease_issuable         : yes" in check
    assert "requested_action_scope : memory.recall" in check
    assert "requested_capability   : memory.read.project_context" in check

    lease = commands.dispatch(
        [
            "run",
            "lease-issue",
            "--effect",
            "memory-recall",
            "--confirm",
            LEASE_ID,
        ]
    )
    assert "issued                      : yes" in lease
    assert "creates_audit_event         : yes" in lease
    assert "executes                    : no" in lease

    executed = commands.dispatch(
        [
            "run",
            "execute-memory-recall",
            "--confirm",
            LEASE_ID,
            "--query",
            "governed memory",
            "--wing",
            "repo:/tmp/project",
            "--limit",
            "3",
        ]
    )
    assert "executed                    : yes" in executed
    assert "bounded_effect              : yes" in executed
    assert "consumes_lease              : yes" in executed
    assert "mutates_project_os          : yes" in executed
    assert "mutates_kennel              : no" in executed
    assert "creates_audit_event         : yes" in executed
    assert "hit_count                   : 1" in executed
    assert "drawer_id=101" in executed
    assert searches == [("governed memory", "repo:/tmp/project", 3)]

    state = _load_raw(state_file)
    lease_record = state["leases"][LEASE_ID]
    assert lease_record["consumed_at"]
    assert lease_record["consumed_event_id"]
    memory_events = _events_by_type(
        state, memory_recall_execution.MEMORY_RECALL_EFFECT_EVENT_TYPE
    )
    assert len(memory_events) == 1
    assert memory_events[0]["parent_event_id"] == lease_record["issued_event_id"]
    assert "hits=1" in memory_events[0]["payload_summary"]

    after_first = _load_raw(state_file)
    second = commands.dispatch(
        [
            "run",
            "execute-memory-recall",
            "--confirm",
            LEASE_ID,
            "--query",
            "governed memory",
        ]
    )
    assert "executed                    : no" in second
    assert "lease already consumed" in second
    assert searches == [("governed memory", "repo:/tmp/project", 3)]
    assert _load_raw(state_file) == after_first


def test_memory_recall_lease_requires_memory_recall_effect_selection(
    tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run()
    commands.dispatch(
        [
            "authority",
            "grant-create",
            "--effect",
            "memory-recall",
            "--confirm",
            GRANT_ID,
        ]
    )
    before = state_file.read_text(encoding="utf-8")

    result = commands.dispatch(["run", "lease-issue", "--confirm", LEASE_ID])

    assert "issued                      : no" in result
    assert "confirmation mismatch" in result
    assert "lease:run-memory-recall-cli:project_run.execute_bounded_step" in result
    assert state_file.read_text(encoding="utf-8") == before


def test_memory_recall_rejects_empty_query_before_search(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    searches: list[tuple[str, str, int]] = []
    monkeypatch.setattr(
        memory_recall_execution,
        "_default_searcher",
        lambda query, wing, limit: searches.append((query, wing, limit)),
    )

    _create_ready_run()
    commands.dispatch(
        [
            "authority",
            "grant-create",
            "--effect",
            "memory-recall",
            "--confirm",
            GRANT_ID,
        ]
    )
    commands.dispatch(
        [
            "run",
            "lease-issue",
            "--effect",
            "memory-recall",
            "--confirm",
            LEASE_ID,
        ]
    )
    before = state_file.read_text(encoding="utf-8")

    result = memory_recall_execution.execute_memory_recall(
        confirm_lease_id=LEASE_ID,
        query="   ",
    )

    assert not result.executed
    assert result.blockers == ("query missing",)
    assert searches == []
    assert state_file.read_text(encoding="utf-8") == before
