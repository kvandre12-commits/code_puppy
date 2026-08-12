"""Tests for the narrow pydantic-ai history-processing compatibility seam."""

import warnings

from pydantic_ai import Agent

from code_puppy import pydantic_compat


def _first_processor(messages):
    return messages


def _second_processor(messages):
    return messages


def test_history_processor_kwargs_uses_capabilities_when_available(monkeypatch):
    class FakeProcessHistory:
        def __init__(self, processor):
            self.processor = processor

    monkeypatch.setattr(pydantic_compat, "_ProcessHistory", FakeProcessHistory)

    kwargs = pydantic_compat.history_processor_kwargs(
        _first_processor,
        _second_processor,
    )

    assert set(kwargs) == {"capabilities"}
    assert [capability.processor for capability in kwargs["capabilities"]] == [
        _first_processor,
        _second_processor,
    ]


def test_runtime_agent_construction_avoids_pydantic_ai_deprecation_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Agent(**pydantic_compat.history_processor_kwargs(_first_processor))

    assert not [
        warning
        for warning in caught
        if warning.category.__name__ == "PydanticAIDeprecationWarning"
    ]


def test_history_processor_kwargs_falls_back_for_locked_android_runtime(monkeypatch):
    monkeypatch.setattr(pydantic_compat, "_ProcessHistory", None)

    kwargs = pydantic_compat.history_processor_kwargs(
        _first_processor,
        _second_processor,
    )

    assert kwargs == {
        "history_processors": [_first_processor, _second_processor],
    }
