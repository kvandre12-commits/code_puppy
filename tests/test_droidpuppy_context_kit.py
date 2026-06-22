from __future__ import annotations

import json

from code_puppy.plugins.droidpuppy_context_kit.register_callbacks import (
    _advertise_tools_to_agent,
)
from code_puppy.plugins.droidpuppy_context_kit.tooling import (
    droidpuppy_context_apply_packet,
    droidpuppy_context_commit_workflow,
    droidpuppy_context_handshake,
    droidpuppy_context_init,
    droidpuppy_context_packet,
    droidpuppy_context_record,
)


def test_context_handshake_and_commit_pending_approval(tmp_path) -> None:
    root = str(tmp_path / "ctx")
    droidpuppy_context_init(root=root, workflow_id="discord-governance")

    handshake = droidpuppy_context_handshake(
        root=root,
        workflow_id="discord-governance",
        requester="mike",
        raw_request="post a meme to discord safely",
        intent_summary="govern discord posting workflow",
        requested_capabilities=["android.handoff.share"],
        constraints=["no autonomous posting without approval"],
        target_surface="discord",
    )
    assert handshake["success"] is True
    assert handshake["intent_handshake"]["status"] == "handshake_recorded"

    packet_update = droidpuppy_context_apply_packet(
        root=root,
        workflow_state_json=json.dumps(
            {
                "summary": "govern discord posting",
                "current_goal": "safe workflow commit",
            }
        ),
        execution_plan_json=json.dumps(
            {"next_steps": ["get approval", "package share payload"]}
        ),
        approval_decision_json=json.dumps(
            {
                "status": "review_required",
                "allowed_actions": [],
                "blocked_actions": ["android.handoff.share"],
            }
        ),
    )
    assert packet_update["success"] is True

    commit = droidpuppy_context_commit_workflow(
        root=root,
        workflow_id="discord-governance",
        committed_by="mike",
        commit_message="freeze this workflow before skill/tool graduation",
    )
    assert commit["success"] is True
    assert commit["workflow_commit"]["status"] == "committed_pending_approval"
    assert commit["workflow_commit"]["approval_status"] == "review_required"


def test_context_commit_ready_after_approval_and_packet_surfaces_artifacts(
    tmp_path,
) -> None:
    root = str(tmp_path / "ctx")
    droidpuppy_context_init(root=root, workflow_id="workflow-ready")
    droidpuppy_context_handshake(
        root=root,
        workflow_id="workflow-ready",
        requester="mike",
        raw_request="turn this into a governed reusable workflow",
    )
    droidpuppy_context_apply_packet(
        root=root,
        workflow_state_json=json.dumps(
            {"summary": "workflow ready", "current_goal": "commit approved workflow"}
        ),
        execution_plan_json=json.dumps({"next_steps": ["run orchestrator"]}),
        approval_decision_json=json.dumps(
            {
                "status": "approved",
                "allowed_actions": ["invoke governance chain"],
                "evidence_refs": ["docs/AGENT_STACK_GOVERNANCE.md"],
            }
        ),
    )

    commit = droidpuppy_context_commit_workflow(root=root, workflow_id="workflow-ready")
    packet = droidpuppy_context_packet(root=root)

    assert commit["workflow_commit"]["status"] == "committed_ready"
    assert packet["intent_handshake"]["status"] == "handshake_recorded"
    assert packet["workflow_commit"]["status"] == "committed_ready"
    assert packet["workflow_commit"]["allowed_actions_snapshot"] == [
        "invoke governance chain"
    ]


def test_context_record_does_not_mutate_approval_or_clear_existing_state(
    tmp_path,
) -> None:
    root = str(tmp_path / "ctx")
    droidpuppy_context_init(root=root, workflow_id="record-safety")
    droidpuppy_context_apply_packet(
        root=root,
        workflow_state_json=json.dumps({"current_goal": "keep this goal"}),
        approval_decision_json=json.dumps(
            {
                "status": "approved",
                "allowed_actions": ["invoke governance chain"],
            }
        ),
    )

    record = droidpuppy_context_record(
        root=root,
        what="observed fresh evidence",
        why="journal the latest fact without changing authority",
        result="recorded",
        actor="mike",
    )
    packet = droidpuppy_context_packet(root=root)

    assert record["success"] is True
    assert packet["packet"]["workflow_state"]["current_goal"] == "keep this goal"
    assert packet["packet"]["approval_decision"]["status"] == "approved"
    assert packet["packet"]["approval_decision"]["allowed_actions"] == [
        "invoke governance chain"
    ]


def test_context_tools_are_only_advertised_to_governance_agents() -> None:
    assert "droidpuppy_context_packet" in _advertise_tools_to_agent("code-puppy")
    assert "droidpuppy_context_commit_workflow" in _advertise_tools_to_agent(
        "workflow-commit"
    )
    assert "droidpuppy_context_packet" in _advertise_tools_to_agent("lease-request")
    assert "droidpuppy_context_append_journal" in _advertise_tools_to_agent(
        "lease-audit"
    )
    assert "droidpuppy_context_install_repo_governance" in _advertise_tools_to_agent(
        "code-puppy"
    )
    assert _advertise_tools_to_agent("split-my-pr") == []
    assert _advertise_tools_to_agent(None) == []
