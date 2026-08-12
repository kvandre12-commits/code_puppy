from __future__ import annotations

import json

from code_puppy.plugins.droidpuppy_context_kit.register_callbacks import (
    _advertise_tools_to_agent,
)
from code_puppy.plugins.droidpuppy_context_kit.tooling import (
    droidpuppy_context_apply_packet,
    droidpuppy_context_commit_workflow,
    droidpuppy_context_fast_path_status,
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


def test_handshake_rejects_cross_workflow_retagging(tmp_path) -> None:
    root = str(tmp_path / "ctx")
    droidpuppy_context_init(root=root, workflow_id="existing-workflow")

    result = droidpuppy_context_handshake(
        root=root,
        workflow_id="different-workflow",
        requester="mike",
        raw_request="start unrelated work",
    )

    assert result["success"] is False
    assert "workflow_id mismatch" in result["reason"]
    packet = droidpuppy_context_packet(root=root)
    assert packet["workflow_id"] == "existing-workflow"
    assert packet["intent_handshake"]["workflow_id"] == "existing-workflow"


def test_apply_packet_rejects_cross_workflow_authority_merge(tmp_path) -> None:
    root = str(tmp_path / "ctx")
    droidpuppy_context_init(root=root, workflow_id="existing-workflow")

    result = droidpuppy_context_apply_packet(
        root=root,
        approval_decision_json=json.dumps(
            {
                "workflow_id": "different-workflow",
                "status": "approved",
                "allowed_actions": ["unrelated action"],
            }
        ),
    )

    assert result["success"] is False
    assert "workflow_id mismatch" in result["reason"]
    approval = droidpuppy_context_packet(root=root)["packet"]["approval_decision"]
    assert approval["workflow_id"] == "existing-workflow"
    assert approval["status"] == "review_required"
    assert approval["allowed_actions"] == []


def test_apply_packet_rejects_conflicting_workflow_ids(tmp_path) -> None:
    root = str(tmp_path / "ctx")
    droidpuppy_context_init(root=root, workflow_id="existing-workflow")

    result = droidpuppy_context_apply_packet(
        root=root,
        workflow_state_json=json.dumps({"workflow_id": "first-workflow"}),
        approval_decision_json=json.dumps({"workflow_id": "second-workflow"}),
    )

    assert result == {
        "success": False,
        "reason": "packet patches contain conflicting workflow_id values",
    }


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


def test_fast_path_status_is_eligible_for_committed_matching_workflow(tmp_path) -> None:
    root = str(tmp_path / "ctx")
    droidpuppy_context_init(root=root, workflow_id="dashboard-open")
    droidpuppy_context_handshake(
        root=root,
        workflow_id="dashboard-open",
        requester="mike",
        raw_request="start the local SharpEdge dashboard and open it in Brave",
        intent_summary="open dashboard in brave",
    )
    droidpuppy_context_apply_packet(
        root=root,
        workflow_state_json=json.dumps(
            {
                "summary": "open dashboard in brave",
                "current_goal": "reuse committed workflow",
            }
        ),
        approval_decision_json=json.dumps(
            {
                "status": "lease_ready",
                "allowed_actions": ["start dashboard and open brave"],
                "lease_request": {
                    "capabilities": ["shell.process.exec", "android.browser.open_url"]
                },
            }
        ),
    )
    droidpuppy_context_commit_workflow(root=root, workflow_id="dashboard-open")

    result = droidpuppy_context_fast_path_status(
        root=root,
        workflow_id="dashboard-open",
        raw_request="open the dashboard in brave",
    )

    assert result["success"] is True
    assert result["eligible"] is True
    assert result["fast_path"]["commit_status"] == "committed_ready"
    assert result["fast_path"]["scope_match"] is True


def test_fast_path_status_rejects_scope_drift(tmp_path) -> None:
    root = str(tmp_path / "ctx")
    droidpuppy_context_init(root=root, workflow_id="dashboard-open")
    droidpuppy_context_handshake(
        root=root,
        workflow_id="dashboard-open",
        requester="mike",
        raw_request="open the SharpEdge dashboard in Brave",
    )
    droidpuppy_context_apply_packet(
        root=root,
        approval_decision_json=json.dumps(
            {
                "status": "approved",
                "lease_request": {"capabilities": ["android.browser.open_url"]},
            }
        ),
    )
    droidpuppy_context_commit_workflow(
        root=root,
        workflow_id="dashboard-open",
        commit_message="committed for dashboard open",
    )

    result = droidpuppy_context_fast_path_status(
        root=root,
        workflow_id="dashboard-open",
        raw_request="delete the repo and text everyone",
    )

    assert result["success"] is True
    assert result["eligible"] is False
    assert "scope" in " ".join(result["blockers"]).lower()


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
    assert "droidpuppy_context_fast_path_status" in _advertise_tools_to_agent(
        "governance-orchestrator"
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
