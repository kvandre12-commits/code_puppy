import json

from code_puppy.plugins.chatgpt_robinhood_delegate.register_callbacks import (
    _advertise_tools_to_agent,
)
from code_puppy.plugins.chatgpt_robinhood_delegate.tooling import (
    DEFAULT_ARTIFACT_NAME,
    build_delegation_packet,
    build_delegation_prompt,
    write_delegation_artifacts,
)


def test_build_delegation_packet_coerces_live_order_policy():
    packet, warnings = build_delegation_packet(
        task_type="order_submit",
        objective="Buy 10 shares of HOOD if approved.",
        broker_payload_json='{"symbol": "HOOD", "side": "buy", "quantity": 10}',
        approval_policy="do_it_now",
    )

    assert packet["task_type"] == "order_submit"
    assert packet["approval_policy"] == "operator_confirm_required"
    assert packet["broker_payload"]["symbol"] == "HOOD"
    assert warnings
    assert "coerced" in warnings[0]


def test_build_delegation_packet_keeps_invalid_json_as_raw_text():
    packet, warnings = build_delegation_packet(
        task_type="market_data",
        objective="Check HOOD price action.",
        broker_payload_json="symbol=HOOD side=watch",
    )

    assert packet["broker_payload"] == {"raw_text": "symbol=HOOD side=watch"}
    assert warnings
    assert "raw_text" in warnings[0]


def test_build_delegation_prompt_mentions_connector_and_payload():
    packet, _ = build_delegation_packet(
        task_type="account_read",
        objective="Summarize buying power.",
        broker_payload_json='{"fields": ["buying_power"]}',
    )

    prompt = build_delegation_prompt(packet)

    assert "Robinhood connector" in prompt
    assert "Summarize buying power." in prompt
    assert '"buying_power"' in prompt


def test_write_delegation_artifacts_creates_json_and_text_files(tmp_path):
    packet, _ = build_delegation_packet(
        task_type="other",
        objective="Do the thing.",
    )
    prompt = build_delegation_prompt(packet)

    json_path, text_path = write_delegation_artifacts(
        packet,
        prompt,
        artifact_name=DEFAULT_ARTIFACT_NAME,
        base_dir=tmp_path,
    )

    assert json_path.exists()
    assert text_path.exists()
    assert (
        json.loads(json_path.read_text(encoding="utf-8"))["objective"]
        == "Do the thing."
    )
    assert "Do the thing." in text_path.read_text(encoding="utf-8")


def test_register_agent_tools_advertises_delegate_tool():
    assert _advertise_tools_to_agent("anything") == ["chatgpt_robinhood_delegate"]
