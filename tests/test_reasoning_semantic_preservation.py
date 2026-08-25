"""Contract tests for Responses reasoning replay preservation.

These tests intentionally exercise cases where history retention alone is not
sufficient: a retained assistant message is only replayable if the provider-owned
reasoning item that authorizes it survives stream reconstruction unchanged.
"""

import json
from unittest.mock import Mock

import httpx
import pytest

from code_puppy.chatgpt_codex_client import ChatGPTCodexAsyncClient


def _stream_response(events: list[dict]):
    sse_lines = [f"data: {json.dumps(event)}" for event in events]
    sse_lines.append("data: [DONE]")

    async def mock_aiter_lines():
        for line in sse_lines:
            yield line

    response = Mock(spec=httpx.Response)
    response.status_code = 200
    response.headers = {}
    response.aiter_lines = mock_aiter_lines
    response.request = Mock()
    return response


@pytest.mark.asyncio
async def test_partial_completed_envelope_cannot_orphan_retained_message():
    """A message must not outlive the reasoning item required to replay it."""
    reasoning = {
        "type": "reasoning",
        "id": "rs_contract",
        "encrypted_content": "opaque-replay-state",
        "summary": [],
    }
    message = {
        "type": "message",
        "id": "msg_contract",
        "role": "assistant",
        "content": [{"type": "output_text", "text": "answer"}],
    }

    response = _stream_response(
        [
            {"type": "response.output_item.done", "item": reasoning},
            {"type": "response.output_item.done", "item": message},
            {
                "type": "response.completed",
                "response": {"id": "resp_contract", "output": [message]},
            },
        ]
    )

    result = await ChatGPTCodexAsyncClient()._convert_stream_to_response(response)
    output = json.loads(result.content)["output"]

    assert output == [reasoning, message]
    assert output[0]["id"] == "rs_contract"
    assert output[0]["encrypted_content"] == "opaque-replay-state"


@pytest.mark.asyncio
async def test_partial_reasoning_in_completed_envelope_cannot_replace_complete_item():
    """Prefer the complete done item when the final envelope loses replay state."""
    complete_reasoning = {
        "type": "reasoning",
        "id": "rs_complete",
        "encrypted_content": "encrypted-state-that-must-survive",
        "summary": [],
    }
    degraded_reasoning = {
        "type": "reasoning",
        "id": "rs_complete",
        "summary": [],
    }
    message = {
        "type": "message",
        "id": "msg_after_reasoning",
        "role": "assistant",
        "content": [{"type": "output_text", "text": "answer"}],
    }

    response = _stream_response(
        [
            {"type": "response.output_item.done", "item": complete_reasoning},
            {"type": "response.output_item.done", "item": message},
            {
                "type": "response.completed",
                "response": {
                    "id": "resp_partial_reasoning",
                    "output": [degraded_reasoning, message],
                },
            },
        ]
    )

    result = await ChatGPTCodexAsyncClient()._convert_stream_to_response(response)
    output = json.loads(result.content)["output"]

    assert output == [complete_reasoning, message]
    assert output[0]["encrypted_content"] == "encrypted-state-that-must-survive"


@pytest.mark.asyncio
async def test_completed_output_item_order_is_conserved_for_replay():
    """Semantic preservation includes item ordering, not only item membership."""
    reasoning = {
        "type": "reasoning",
        "id": "rs_order",
        "encrypted_content": "ordered-replay-state",
        "summary": [],
    }
    tool_call = {
        "type": "function_call",
        "id": "fc_order",
        "call_id": "call_order",
        "name": "lookup",
        "arguments": "{}",
    }
    message = {
        "type": "message",
        "id": "msg_order",
        "role": "assistant",
        "content": [{"type": "output_text", "text": "done"}],
    }

    response = _stream_response(
        [
            {"type": "response.output_item.done", "item": reasoning},
            {"type": "response.output_item.done", "item": tool_call},
            {"type": "response.output_item.done", "item": message},
            {
                "type": "response.completed",
                "response": {"id": "resp_order", "output": [message]},
            },
        ]
    )

    result = await ChatGPTCodexAsyncClient()._convert_stream_to_response(response)
    output = json.loads(result.content)["output"]

    assert [item["type"] for item in output] == [
        "reasoning",
        "function_call",
        "message",
    ]
    assert output[0]["encrypted_content"] == "ordered-replay-state"
    assert output[1]["call_id"] == "call_order"
    assert output[2]["id"] == "msg_order"


# Touch this test-only branch to trigger pull-request CI after retargeting to the #853 head.
