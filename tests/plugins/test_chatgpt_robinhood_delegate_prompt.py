import json

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


def test_build_delegation_prompt_renders_payload_contracts_plan():
    packet, _ = build_delegation_packet(
        task_type="order_submit",
        objective="Execute the prepared SPY option flow if confirmed.",
        broker_payload_json=json.dumps(
            {
                "symbol": "SPY",
                "side": "buy",
                "quantity": 1,
                "payload_contracts": {
                    "schema": "sharpedge.connector_payload_contracts.v1",
                    "read_contracts": {
                        "account_read_probe": {
                            "contract_type": "account_read_probe",
                            "requested_checks": [
                                "get_accounts",
                                "get_option_positions",
                            ],
                            "safe_output": "masked_accounts_only",
                        }
                    },
                    "execution_contracts": [
                        {
                            "step_id": "single_step",
                            "intent_stage": "entry",
                            "position_effect": "open",
                            "lookup_contract": {
                                "tool_sequence": [
                                    {
                                        "tool_name": "get_option_chains",
                                        "payload": {"underlying_symbol": "SPY"},
                                    },
                                    {
                                        "tool_name": "get_option_instruments",
                                        "payload": {
                                            "chain_symbol": "SPY",
                                            "expiration_dates": "2026-06-15",
                                            "type": "call",
                                        },
                                    },
                                ],
                                "selection_policy": {
                                    "policy_name": "odte_otm_ladder",
                                    "candidate_strikes": [501.0, 502.0, 503.0, 504.0],
                                },
                            },
                            "review_contract": {
                                "tool_name": "review_option_order",
                                "payload_template": {
                                    "account_number": "<required_agentic_allowed_account>",
                                    "quantity": "1",
                                    "price": "1.23",
                                    "legs": [
                                        {
                                            "option_id": "<resolved_option_id>",
                                            "side": "buy",
                                            "position_effect": "open",
                                        }
                                    ],
                                },
                            },
                            "submit_contract": {
                                "tool_name": "place_option_order",
                                "payload_template": {
                                    "account_number": "<required_agentic_allowed_account>",
                                    "legs": [
                                        {
                                            "option_id": "<resolved_option_id>",
                                            "side": "buy",
                                            "position_effect": "open",
                                        }
                                    ],
                                },
                            },
                        }
                    ],
                },
            }
        ),
    )

    prompt = build_delegation_prompt(packet)

    assert "Connector contract plan:" in prompt
    assert "Read-side contracts:" in prompt
    assert "Execution-side contracts:" in prompt
    assert "get_option_chains" in prompt
    assert "candidate ladder 501.0, 502.0, 503.0, 504.0" in prompt
    assert "review phase: review_option_order" in prompt
    assert "submit phase: place_option_order" in prompt


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
