from code_puppy.openai_capabilities import (
    get_openai_reasoning_effort_choices,
    infer_openai_transport,
    merge_openai_metadata,
    normalize_openai_reasoning_effort,
    supports_openai_reasoning_payload,
    supports_openai_xhigh_reasoning,
)


def test_infer_openai_transport_honors_explicit_override():
    assert infer_openai_transport("gpt-5.6-sol", {"openai_transport": "chat"}) == "chat"


def test_infer_openai_transport_detects_sol_and_foundry_gpt5():
    assert (
        infer_openai_transport(
            "gpt-5.6-sol",
            {"type": "openai", "openai_family": "sol", "name": "gpt-5.6-sol"},
        )
        == "responses"
    )
    assert (
        infer_openai_transport(
            "foundry-gpt-5-4",
            {"type": "azure_foundry_openai", "name": "gpt-5.4"},
        )
        == "responses"
    )


def test_supports_openai_xhigh_reasoning_for_sol_only_when_expected():
    assert supports_openai_xhigh_reasoning("gpt-5.6-sol") is True
    assert supports_openai_xhigh_reasoning("gpt-5.4") is True
    assert supports_openai_xhigh_reasoning("gpt-5.2") is False


def test_get_openai_reasoning_effort_choices_tracks_model_family():
    assert get_openai_reasoning_effort_choices("gpt-5.6-sol") == (
        "none",
        "low",
        "medium",
        "high",
        "xhigh",
        "max",
    )
    assert get_openai_reasoning_effort_choices("gpt-5.5") == (
        "minimal",
        "low",
        "medium",
        "high",
        "xhigh",
    )
    assert get_openai_reasoning_effort_choices("gpt-5.2") == (
        "minimal",
        "low",
        "medium",
        "high",
    )


def test_normalize_openai_reasoning_effort_maps_between_model_realities():
    assert normalize_openai_reasoning_effort("gpt-5.6-sol", "minimal") == "none"
    assert normalize_openai_reasoning_effort("gpt-5.5", "none") == "minimal"
    assert normalize_openai_reasoning_effort("gpt-5.5", "max") == "xhigh"
    assert normalize_openai_reasoning_effort("gpt-5.2", "max") == "high"


def test_merge_openai_metadata_adds_sol_responses_fields():
    merged = merge_openai_metadata(
        "gpt-5.6-sol",
        {"type": "openai", "name": "gpt-5.6-sol", "openai_family": "sol"},
        supported_settings=["temperature", "top_p"],
    )

    assert merged["openai_transport"] == "responses"
    assert merged["supports_xhigh_reasoning"] is True
    assert merged["reasoning_effort_choices"] == [
        "none",
        "low",
        "medium",
        "high",
        "xhigh",
        "max",
    ]
    assert merged["supported_settings"] == [
        "temperature",
        "top_p",
        "reasoning_effort",
        "summary",
        "verbosity",
    ]


def test_supports_openai_reasoning_payload_includes_sol_family():
    assert supports_openai_reasoning_payload("gpt-5.6-sol") is True
    assert supports_openai_reasoning_payload("gpt-4.1") is False
