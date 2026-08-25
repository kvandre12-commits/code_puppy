from pydantic_ai.messages import ModelResponse, ThinkingPart

from code_puppy.agents._compaction import _strip_empty_thinking_parts


def test_preserve_empty_signed_thinking_part():
    message = ModelResponse(
        [ThinkingPart(content="", id="rs_1", signature="encrypted")]
    )

    cleaned, filtered = _strip_empty_thinking_parts([message])

    assert cleaned == [message]
    assert filtered == 0


def test_remove_empty_unsigned_thinking_part():
    message = ModelResponse([ThinkingPart(content="", id="rs_1")])

    cleaned, filtered = _strip_empty_thinking_parts([message])

    assert cleaned == []
    assert filtered == 1


def test_signed_empty_reasoning_survives_when_unsigned_sibling_is_removed():
    """Cleanup may remove junk, but it must not remove replay authority."""
    signed = ThinkingPart(content="", id="rs_signed", signature="opaque-replay-token")
    unsigned = ThinkingPart(content="", id="rs_unsigned")
    message = ModelResponse([unsigned, signed])

    cleaned, filtered = _strip_empty_thinking_parts([message])

    assert filtered == 1
    assert len(cleaned) == 1
    assert cleaned[0].parts == [signed]
    assert cleaned[0].parts[0].id == "rs_signed"
    assert cleaned[0].parts[0].signature == "opaque-replay-token"


def test_reasoning_replay_fields_are_not_mutated_by_cleanup():
    """Preservation means byte-for-byte field survival, not mere part retention."""
    signed = ThinkingPart(
        content="",
        id="rs_critical",
        signature="encrypted-reasoning-state",
    )
    message = ModelResponse([signed])

    cleaned, filtered = _strip_empty_thinking_parts([message])

    assert filtered == 0
    assert len(cleaned) == 1
    preserved = cleaned[0].parts[0]
    assert isinstance(preserved, ThinkingPart)
    assert preserved.content == ""
    assert preserved.id == "rs_critical"
    assert preserved.signature == "encrypted-reasoning-state"
