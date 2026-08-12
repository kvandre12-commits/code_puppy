import json
from pathlib import Path

import pytest

from code_puppy.plugins.chatgpt_robinhood_delegate.register_callbacks import (
    _advertise_tools_to_agent,
    register_tools_callback,
)
from code_puppy.plugins.chatgpt_robinhood_delegate.audit import (
    DEFAULT_AUDIT_ARTIFACT_NAME,
    build_connector_audit_packet,
    ingest_connector_audit,
)
from code_puppy.plugins.chatgpt_robinhood_delegate.loop import (
    DEFAULT_LOOP_ARTIFACT_NAME,
    finish_delegation_loop,
    get_delegation_loop_status,
    start_delegation_loop,
)
from code_puppy.plugins.chatgpt_robinhood_delegate.tooling import (
    DEFAULT_BRIDGE_ARTIFACT_NAME,
    build_delegation_packet_from_bridge_handoff,
    prepare_delegation_from_bridge_handoff,
    prepare_delegation_from_signal,
)


def _write_bridge_handoff(tmp_path, payload):
    path = tmp_path / "robinhood_execution_handoff.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_fake_bridge_repo(tmp_path, payload):
    bridge_root = tmp_path / "SharpEdge-Robinhood-Bridge"
    package_dir = bridge_root / "src" / "sharpedge_robinhood_bridge"
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    payload_json = json.dumps(payload)
    (package_dir / "__main__.py").write_text(
        """
import json
import sys
from pathlib import Path

PAYLOAD = """
        + repr(payload_json)
        + """


def _arg(flag: str, default: str = "") -> str:
    if flag in sys.argv:
        index = sys.argv.index(flag)
        if index + 1 < len(sys.argv):
            return sys.argv[index + 1]
    return default


out_dir = Path(_arg("--out-dir", ".")).expanduser()
latest_name = _arg("--latest-name", "robinhood_execution_handoff.json")
out_dir.mkdir(parents=True, exist_ok=True)
path = out_dir / latest_name
path.write_text(PAYLOAD, encoding="utf-8")
print(json.dumps({"artifact_path": str(path)}))
""",
        encoding="utf-8",
    )
    return bridge_root


def test_build_delegation_packet_from_bridge_handoff_maps_trade_packet(tmp_path):
    handoff_path = _write_bridge_handoff(
        tmp_path,
        {
            "schema": "sharpedge.robinhood_execution_handoff.v1",
            "source": {"signal_path": "~/SharpEdge-System/outputs/signal.json"},
            "signal_summary": {"symbol": "SPY", "trade_gate": "pass"},
            "decision": {"action": "trade", "reason": "confirmed bullish runner"},
            "command_plan": {
                "command": "order_submit",
                "route": "chatgpt_delegate",
                "approval_policy": "operator_confirm_required",
                "status": "awaiting_operator_confirm",
            },
            "delegation": {
                "task_type": "order_submit",
                "broker_payload": {"symbol": "SPY", "side": "buy", "quantity": 1},
                "constraints": "Do not execute without explicit operator confirmation.",
                "risk_notes": "Tiny-size bridge path.",
                "required_result": "Return the exact order draft.",
            },
            "operator_gate": {"required": True},
            "notes": ["Route through approval-gated delegate flow."],
            "risk": {"ok": True, "blocks": [], "notes": ["Within ceiling."]},
        },
    )

    packet, warnings = build_delegation_packet_from_bridge_handoff(
        handoff_path=handoff_path,
    )

    assert packet["task_type"] == "order_submit"
    assert packet["approval_policy"] == "operator_confirm_required"
    assert packet["broker_payload"]["symbol"] == "SPY"
    assert "SharpEdge bridge handoff" in packet["objective"]
    assert "confirmed bullish runner" in packet["supporting_context"]
    assert "Within ceiling." in packet["risk_notes"]
    assert not warnings


def test_build_delegation_packet_from_bridge_handoff_rejects_stand_down(tmp_path):
    handoff_path = _write_bridge_handoff(
        tmp_path,
        {
            "schema": "sharpedge.robinhood_execution_handoff.v1",
            "decision": {"action": "stand_down", "reason": "no edge"},
            "command_plan": {"route": "not_applicable", "status": "stand_down"},
            "delegation": {"broker_payload": {}},
            "operator_gate": {"required": False},
        },
    )

    with pytest.raises(ValueError, match="not 'trade'"):
        build_delegation_packet_from_bridge_handoff(handoff_path=handoff_path)


def test_prepare_delegation_from_bridge_handoff_writes_artifacts(tmp_path):
    handoff_path = _write_bridge_handoff(
        tmp_path,
        {
            "schema": "sharpedge.robinhood_execution_handoff.v1",
            "source": {"signal_path": "~/SharpEdge-System/outputs/signal.json"},
            "signal_summary": {"symbol": "SPY"},
            "decision": {"action": "trade", "reason": "test mode"},
            "command_plan": {
                "command": "order_submit",
                "route": "chatgpt_delegate",
                "approval_policy": "operator_confirm_required",
                "status": "awaiting_operator_confirm",
            },
            "delegation": {
                "task_type": "order_submit",
                "broker_payload": {"symbol": "SPY", "side": "buy", "quantity": 1},
                "constraints": "Do not execute without explicit operator confirmation.",
                "risk_notes": "Tiny-size bridge path.",
                "required_result": "Return the exact order draft.",
            },
            "operator_gate": {"required": True},
            "risk": {"ok": True, "blocks": [], "notes": []},
        },
    )

    result = prepare_delegation_from_bridge_handoff(
        handoff_path=handoff_path,
        artifact_name=DEFAULT_BRIDGE_ARTIFACT_NAME,
        base_dir=tmp_path,
    )

    assert result.status == "prepared"
    assert result.task_type == "order_submit"
    assert (tmp_path / "outputs" / f"{DEFAULT_BRIDGE_ARTIFACT_NAME}.json").exists()
    assert (tmp_path / "outputs" / f"{DEFAULT_BRIDGE_ARTIFACT_NAME}.txt").exists()


def test_prepare_delegation_from_signal_runs_bridge_then_writes_artifacts(tmp_path):
    bridge_root = _write_fake_bridge_repo(
        tmp_path,
        {
            "schema": "sharpedge.robinhood_execution_handoff.v1",
            "source": {"signal_path": "~/SharpEdge-System/outputs/signal.json"},
            "signal_summary": {"symbol": "SPY", "trade_gate": "pass"},
            "decision": {"action": "trade", "reason": "bridge runner"},
            "command_plan": {
                "command": "order_submit",
                "route": "chatgpt_delegate",
                "approval_policy": "operator_confirm_required",
                "status": "awaiting_operator_confirm",
            },
            "delegation": {
                "task_type": "order_submit",
                "broker_payload": {"symbol": "SPY", "side": "buy", "quantity": 1},
                "constraints": "Do not execute without explicit operator confirmation.",
                "risk_notes": "Bridge path.",
                "required_result": "Return the exact order draft.",
            },
            "operator_gate": {"required": True},
            "risk": {"ok": True, "blocks": [], "notes": ["Bridge ok."]},
        },
    )

    result = prepare_delegation_from_signal(
        bridge_root=bridge_root,
        handoff_output_dir=tmp_path / "handoffs",
        artifact_name="from-signal",
        base_dir=tmp_path,
        test=True,
    )

    assert result.status == "prepared"
    assert result.task_type == "order_submit"
    assert result.source_handoff_path.endswith("robinhood_execution_handoff.json")
    assert (tmp_path / "outputs" / "from-signal.json").exists()
    assert (tmp_path / "outputs" / "from-signal.txt").exists()


def test_prepare_delegation_from_signal_rejects_non_ready_bridge_handoff(tmp_path):
    bridge_root = _write_fake_bridge_repo(
        tmp_path,
        {
            "schema": "sharpedge.robinhood_execution_handoff.v1",
            "decision": {"action": "stand_down", "reason": "no edge"},
            "command_plan": {"route": "not_applicable", "status": "stand_down"},
            "delegation": {"broker_payload": {}},
            "operator_gate": {"required": False},
        },
    )

    with pytest.raises(ValueError, match="not connector-ready"):
        prepare_delegation_from_signal(
            bridge_root=bridge_root,
            handoff_output_dir=tmp_path / "handoffs",
            base_dir=tmp_path,
        )


def test_build_connector_audit_packet_enriches_from_bridge_handoff(tmp_path):
    handoff_path = _write_bridge_handoff(
        tmp_path,
        {
            "schema": "sharpedge.robinhood_execution_handoff.v1",
            "signal_summary": {"symbol": "SPY", "trade_gate": "pass"},
            "decision": {"action": "trade", "reason": "gap-fill follow-through"},
            "command_plan": {
                "command": "order_submit",
                "route": "chatgpt_delegate",
                "approval_policy": "operator_confirm_required",
                "status": "awaiting_operator_confirm",
            },
            "delegation": {
                "task_type": "order_submit",
                "required_result": "Return the exact order draft.",
                "broker_payload": {"symbol": "SPY", "side": "buy", "quantity": 1},
            },
            "operator_gate": {"required": True},
            "risk": {"notes": ["Stay tiny."]},
        },
    )

    audit_packet, warnings = build_connector_audit_packet(
        response_json=json.dumps(
            {
                "status": "drafted",
                "connector_summary": "Draft created successfully. Awaiting final confirmation.",
                "questions": ["Confirm limit price?"],
                "order_id": "draft-123",
            }
        ),
        handoff_path=str(handoff_path),
    )

    assert audit_packet["schema"] == "sharpedge.robinhood_connector_audit.v1"
    assert audit_packet["requested_action"]["task_type"] == "order_submit"
    assert audit_packet["requested_action"]["symbol"] == "SPY"
    assert audit_packet["connector_observation"]["connector_status"] == "drafted"
    assert audit_packet["connector_observation"]["fill_status"] == "not_submitted"
    assert (
        audit_packet["bridge_context"]["decision_reason"] == "gap-fill follow-through"
    )
    assert audit_packet["operator_follow_up"]["required"] is True
    assert not warnings


def test_ingest_connector_audit_writes_artifacts_and_log(tmp_path):
    handoff_path = _write_bridge_handoff(
        tmp_path,
        {
            "schema": "sharpedge.robinhood_execution_handoff.v1",
            "signal_summary": {"symbol": "SPY", "trade_gate": "pass"},
            "decision": {"action": "trade", "reason": "opening drive continuation"},
            "command_plan": {
                "command": "order_submit",
                "route": "chatgpt_delegate",
                "approval_policy": "operator_confirm_required",
                "status": "awaiting_operator_confirm",
            },
            "delegation": {
                "task_type": "order_submit",
                "broker_payload": {"symbol": "SPY", "side": "buy", "quantity": 1},
            },
            "operator_gate": {"required": True},
        },
    )
    response_path = tmp_path / "connector_response.txt"
    response_path.write_text(
        """Connector says:\n```json
{"status": "submitted", "fill_status": "partial fill", "broker_order_id": "abc-123", "summary": "Submitted to Robinhood and partially filled."}
```\n""",
        encoding="utf-8",
    )

    result = ingest_connector_audit(
        response_file_path=str(response_path),
        handoff_path=str(handoff_path),
        artifact_name=DEFAULT_AUDIT_ARTIFACT_NAME,
        base_dir=tmp_path,
    )

    assert result.status == "recorded"
    assert result.connector_status == "submitted"
    assert result.fill_status == "partial_fill"
    assert result.broker_order_id == "abc-123"
    assert (tmp_path / "outputs" / f"{DEFAULT_AUDIT_ARTIFACT_NAME}.json").exists()
    assert (
        tmp_path / "outputs" / f"{DEFAULT_AUDIT_ARTIFACT_NAME}_journal_stub.json"
    ).exists()
    markdown_path = (
        tmp_path / "outputs" / f"{DEFAULT_AUDIT_ARTIFACT_NAME}_journal_stub.md"
    )
    assert markdown_path.exists()
    assert "Operator fields to confirm" in markdown_path.read_text(encoding="utf-8")
    log_path = tmp_path / "outputs" / "robinhood_connector_audit_log.jsonl"
    assert log_path.exists()
    assert "partial_fill" in log_path.read_text(encoding="utf-8")


def test_build_connector_audit_packet_blocks_freeform_failure_without_handoff():
    audit_packet, warnings = build_connector_audit_packet(
        response_text="Blocked: missing limit price and contract expiration."
    )

    assert audit_packet["requested_action"]["task_type"] == "other"
    assert audit_packet["connector_observation"]["connector_status"] == "blocked"
    assert audit_packet["connector_observation"]["blockers"] == [
        "Blocked: missing limit price and contract expiration."
    ]
    assert warnings == []


def test_ingest_connector_audit_writes_live_positions_snapshot_from_account_read(
    tmp_path,
):
    response = {
        "status": "filled",
        "summary": "Fetched current live positions.",
        "positions": [
            {
                "asset_type": "option",
                "symbol": "SPY",
                "right": "put",
                "quantity": 1,
                "status": "open",
                "strike": 590,
                "expiration_date": "2026-06-26",
                "option_id": "opt-123",
            },
            {
                "asset_type": "equity",
                "symbol": "HOOD",
                "quantity": 5,
                "status": "open",
                "average_buy_price": 75.25,
            },
        ],
        "buying_power": "1234.56",
    }

    result = ingest_connector_audit(
        response_json=json.dumps(response),
        handoff_path=str(
            _write_bridge_handoff(
                tmp_path,
                {
                    "schema": "sharpedge.robinhood_execution_handoff.v1",
                    "signal_summary": {"symbol": "SPY", "trade_gate": "hold"},
                    "decision": {
                        "action": "stand_down",
                        "reason": "read account state",
                    },
                    "command_plan": {
                        "command": "account_read",
                        "route": "chatgpt_delegate",
                        "approval_policy": "read_only",
                        "status": "ready",
                    },
                    "delegation": {
                        "task_type": "account_read",
                        "broker_payload": {"fields": ["positions"]},
                    },
                    "operator_gate": {"required": False},
                },
            )
        ),
        artifact_name=DEFAULT_AUDIT_ARTIFACT_NAME,
        base_dir=tmp_path,
    )

    snapshot_path = tmp_path / "outputs" / "robinhood_live_positions.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert result.live_positions_json_path == str(snapshot_path)
    assert snapshot["schema"] == "sharpedge.robinhood_live_positions.v1"
    assert snapshot["counts"]["option_positions"] == 1
    assert snapshot["counts"]["equity_positions"] == 1
    assert snapshot["option_positions"][0]["right"] == "put"
    assert snapshot["positions"][0]["asset_type"] == "option"


def test_start_delegation_loop_writes_manifest_and_delegation_artifacts(tmp_path):
    bridge_root = _write_fake_bridge_repo(
        tmp_path,
        {
            "schema": "sharpedge.robinhood_execution_handoff.v1",
            "source": {"signal_path": "~/SharpEdge-System/outputs/signal.json"},
            "signal_summary": {"symbol": "SPY", "trade_gate": "pass"},
            "decision": {"action": "trade", "reason": "loop runner"},
            "command_plan": {
                "command": "order_submit",
                "route": "chatgpt_delegate",
                "approval_policy": "operator_confirm_required",
                "status": "awaiting_operator_confirm",
            },
            "delegation": {
                "task_type": "order_submit",
                "broker_payload": {"symbol": "SPY", "side": "buy", "quantity": 1},
                "constraints": "Do not execute without confirmation.",
                "risk_notes": "Loop test path.",
                "required_result": "Return the exact order draft.",
            },
            "operator_gate": {"required": True},
            "risk": {"ok": True, "blocks": [], "notes": []},
        },
    )

    result = start_delegation_loop(
        bridge_root=bridge_root,
        handoff_output_dir=tmp_path / "handoffs",
        artifact_name=DEFAULT_LOOP_ARTIFACT_NAME,
        base_dir=tmp_path,
        test=True,
    )

    loop_state = json.loads(Path(result.loop_json_path).read_text(encoding="utf-8"))
    assert result.status == "prepared"
    assert result.phase == "prepared"
    assert Path(result.delegation_json_path).exists()
    assert Path(result.delegation_text_path).exists()
    assert loop_state["status"] == "awaiting_connector_response"
    assert loop_state["delegation"]["task_type"] == "order_submit"
    assert loop_state["audit"]["artifact_name"] == f"{DEFAULT_LOOP_ARTIFACT_NAME}_audit"


def test_finish_delegation_loop_ingests_response_and_updates_manifest(tmp_path):
    handoff_path = _write_bridge_handoff(
        tmp_path,
        {
            "schema": "sharpedge.robinhood_execution_handoff.v1",
            "signal_summary": {"symbol": "SPY", "trade_gate": "pass"},
            "decision": {"action": "trade", "reason": "loop finish"},
            "command_plan": {
                "command": "order_submit",
                "route": "chatgpt_delegate",
                "approval_policy": "operator_confirm_required",
                "status": "awaiting_operator_confirm",
            },
            "delegation": {
                "task_type": "order_submit",
                "broker_payload": {"symbol": "SPY", "side": "buy", "quantity": 1},
            },
            "operator_gate": {"required": True},
        },
    )
    started = start_delegation_loop(
        handoff_path=str(handoff_path),
        artifact_name=DEFAULT_LOOP_ARTIFACT_NAME,
        base_dir=tmp_path,
    )

    finished = finish_delegation_loop(
        loop_json_path=started.loop_json_path,
        response_json=json.dumps(
            {
                "status": "submitted",
                "fill_status": "partial fill",
                "broker_order_id": "loop-123",
                "summary": "Submitted and partially filled.",
            }
        ),
    )

    loop_state = json.loads(Path(finished.loop_json_path).read_text(encoding="utf-8"))
    assert finished.status == "completed"
    assert finished.audit_json_path.endswith(f"{DEFAULT_LOOP_ARTIFACT_NAME}_audit.json")
    assert Path(finished.audit_json_path).exists()
    assert loop_state["phase"] == "completed"
    assert loop_state["completion"]["connector_status"] == "submitted"
    assert loop_state["completion"]["fill_status"] == "partial_fill"


def test_get_delegation_loop_status_reads_manifest(tmp_path):
    handoff_path = _write_bridge_handoff(
        tmp_path,
        {
            "schema": "sharpedge.robinhood_execution_handoff.v1",
            "signal_summary": {"symbol": "SPY", "trade_gate": "pass"},
            "decision": {"action": "trade", "reason": "status path"},
            "command_plan": {
                "command": "order_submit",
                "route": "chatgpt_delegate",
                "approval_policy": "operator_confirm_required",
                "status": "awaiting_operator_confirm",
            },
            "delegation": {
                "task_type": "order_submit",
                "broker_payload": {"symbol": "SPY", "side": "buy", "quantity": 1},
            },
            "operator_gate": {"required": True},
        },
    )
    started = start_delegation_loop(
        handoff_path=str(handoff_path),
        artifact_name=DEFAULT_LOOP_ARTIFACT_NAME,
        base_dir=tmp_path,
    )

    status = get_delegation_loop_status(loop_json_path=started.loop_json_path)

    assert status.status == "awaiting_connector_response"
    assert status.phase == "prepared"
    assert status.delegation_json_path.endswith("_delegation.json")


def test_register_tools_callback_exposes_one_register_func_per_tool():
    specs = register_tools_callback()

    assert [spec["name"] for spec in specs] == [
        "chatgpt_robinhood_delegate",
        "chatgpt_robinhood_delegate_from_handoff",
        "chatgpt_robinhood_delegate_from_signal",
        "chatgpt_robinhood_audit_ingest",
        "chatgpt_robinhood_loop",
    ]


class _ProbeAgent:
    def __init__(self):
        self.tool_names = []

    def tool(self, func=None):
        def decorator(fn):
            self.tool_names.append(fn.__name__)
            return fn

        if func is None:
            return decorator
        return decorator(func)


@pytest.mark.parametrize(
    ("tool_name", "register_func"),
    [(spec["name"], spec["register_func"]) for spec in register_tools_callback()],
)
def test_each_register_func_registers_exactly_its_named_tool(tool_name, register_func):
    agent = _ProbeAgent()

    register_func(agent)

    assert agent.tool_names == [tool_name]


def test_register_agent_tools_advertises_delegate_tool():
    assert _advertise_tools_to_agent("anything") == [
        "chatgpt_robinhood_delegate",
        "chatgpt_robinhood_delegate_from_handoff",
        "chatgpt_robinhood_delegate_from_signal",
        "chatgpt_robinhood_audit_ingest",
        "chatgpt_robinhood_loop",
    ]
