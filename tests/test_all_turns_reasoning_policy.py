"""Policy-level mutants for GPT-5.6 reasoning_context=all_turns.

These tests bind the configured all_turns policy to provider-shaped reasoning
artifacts that can look empty to generic cleanup code but remain replay-critical.
"""

import json
from unittest.mock import Mock, patch

import httpx
import pytest
from pydantic_ai.messages import ModelResponse, ThinkingPart

from code_puppy.agents._compaction import _strip_empty_thinking_parts
from code_puppy.chatgpt_codex_client import ChatGPTCodexAsyncClient
from code_puppy.model_factory import ModelFactory, make_model_settings


def _all_turns_settings(model_key: str = "luna"):
    config = {
        model_key: {
            "type": "openai",
            "name": "gpt-5.6-luna",
            "context_length": 128000,
        }
    }
    with (
        patch.object(ModelFactory, "load_config", return_value=config),
        patch("code_puppy.config.get_effective_model_settings", return_value={}),
        patch("code_puppy.model_factory.get_yolo_mode", return_value=True),
    ):
        return make_model_settings(model_key)


def _stream_response(events: list[dict]):
    lines = [f"data: {json.dumps(event)}" for event in events] + ["data: [DONE]"]

    async def mock_aiter_lines():
        for line in lines:
            yield line

    response = Mock(spec=httpx.Response)
    response.status_code = 200
    response.headers = {}
    response.aiter_lines = mock_aiter_lines
    response.request = Mock()
    return response


def test_gpt56_alias_defaults_to_all_turns_policy():
    """An alias must inherit GPT-5.6's replay policy from the underlying model."""
    settings = _all_turns_settings("luna")

    assert settings["openai_reasoning_context"] == "all_turns"
    assert settings["openai_reasoning_mode"] == "standard"


def test_all_turns_keeps_empty_signed_internal_reasoning_row():
    """Syntactically empty is not disposable when the row carries replay state."""
    settings = _all_turns_settings()
    signed_empty = ThinkingPart(
        content="",
        id="rs_empty_signed",
        signature="provider-replay-authority",
    )
    unsigned_empty = ThinkingPart(content="", id="rs_empty_unsigned")

    cleaned, _ = _strip_empty_thinking_parts(
        [ModelResponse([unsigned_empty, signed_empty])]
    )

    assert settings["openai_reasoning_context"] == "all_turns"
    assert len(cleaned) == 1
    assert cleaned[0].parts == [signed_empty]
    assert cleaned[0].parts[0].content == ""
    assert cleaned[0].parts[0].id == "rs_empty_signed"
    assert cleaned[0].parts[0].signature == "provider-replay-authority"


@pytest.mark.asyncio
async def test_all_turns_keeps_provider_reasoning_row_with_empty_summary():
    """A provider reasoning row may have no visible summary yet still be required."""
    settings = _all_turns_settings()
    reasoning = {
        "type": "reasoning",
        "id": "rs_provider_empty",
        "encrypted_content": "opaque-provider-state",
        "summary": [],
    }
    message = {
        "type": "message",
        "id": "msg_requires_reasoning",
        "role": "assistant",
        "content": [{"type": "output_text", "text": "answer"}],
    }
    response = _stream_response(
        [
            {"type": "response.output_item.done", "item": reasoning},
            {"type": "response.output_item.done", "item": message},
            {
                "type": "response.completed",
                "response": {"id": "resp_partial", "output": [message]},
            },
        ]
    )

    result = await ChatGPTCodexAsyncClient()._convert_stream_to_response(response)
    output = json.loads(result.content)["output"]

    assert settings["openai_reasoning_context"] == "all_turns"
    assert output == [reasoning, message]
    assert output[0]["summary"] == []
    assert output[0]["encrypted_content"] == "opaque-provider-state"


@pytest.mark.parametrize("summary", [[], None])
@pytest.mark.asyncio
async def test_all_turns_provider_empty_summary_mutants_do_not_orphan_message(summary):
    """Provider-shaped empty-summary variants must remain replayable."""
    settings = _all_turns_settings()
    reasoning = {
        "type": "reasoning",
        "id": f"rs_{summary is None}",
        "encrypted_content": "required-even-when-summary-empty",
        "summary": summary,
    }
    message = {
        "type": "message",
        "id": "msg_mutant",
        "role": "assistant",
        "content": [{"type": "output_text", "text": "ok"}],
    }
    response = _stream_response(
        [
            {"type": "response.output_item.done", "item": reasoning},
            {"type": "response.output_item.done", "item": message},
            {
                "type": "response.completed",
                "response": {"id": "resp_mutant", "output": [message]},
            },
        ]
    )

    result = await ChatGPTCodexAsyncClient()._convert_stream_to_response(response)
    output = json.loads(result.content)["output"]

    assert settings["openai_reasoning_context"] == "all_turns"
    assert output[0] == reasoning
    assert output[1] == message
