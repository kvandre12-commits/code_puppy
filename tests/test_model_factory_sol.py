import os
from unittest.mock import ANY, MagicMock, patch

from code_puppy.model_factory import ModelFactory, make_model_settings


SOL_CONFIG = {
    "gpt-5.6-sol": {
        "type": "openai",
        "name": "gpt-5.6-sol",
        "openai_family": "sol",
        "openai_transport": "responses",
        "supported_settings": ["reasoning_effort", "summary", "verbosity"],
        "reasoning_effort_choices": ["none", "low", "medium", "high", "xhigh", "max"],
        "supports_xhigh_reasoning": True,
    }
}


def test_make_model_settings_for_sol_uses_responses_fields():
    effective_settings = {
        "reasoning_effort": "max",
        "summary": "detailed",
        "verbosity": "medium",
    }
    with (
        patch(
            "code_puppy.model_factory.ModelFactory.load_config", return_value=SOL_CONFIG
        ),
        patch(
            "code_puppy.config.get_effective_model_settings",
            return_value=effective_settings,
        ),
    ):
        settings = make_model_settings("gpt-5.6-sol", max_tokens=4096)

    assert settings["openai_reasoning_effort"] == "max"
    assert settings["openai_reasoning_summary"] == "detailed"
    assert settings["openai_text_verbosity"] == "medium"


def test_openai_sol_uses_responses_model():
    mock_chat = MagicMock()
    mock_responses = MagicMock()

    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        with patch(
            "code_puppy.model_factory._load_openai_model_classes",
            return_value=(mock_chat, MagicMock(), mock_responses, MagicMock()),
        ):
            with patch("code_puppy.model_factory.make_openai_provider"):
                ModelFactory.get_model("gpt-5.6-sol", SOL_CONFIG)

    mock_chat.assert_not_called()
    mock_responses.assert_called_once_with(model_name="gpt-5.6-sol", provider=ANY)


def test_custom_openai_sol_uses_responses_model():
    mock_chat = MagicMock()
    mock_responses = MagicMock()
    custom_config = {
        "gpt-5.6-sol-custom": {
            "type": "custom_openai",
            "name": "gpt-5.6-sol",
            "openai_family": "sol",
            "openai_transport": "responses",
            "custom_endpoint": {"url": "https://api.example.com/v1"},
        }
    }

    with patch("code_puppy.model_factory.create_async_client"):
        with patch(
            "code_puppy.model_factory._load_openai_model_classes",
            return_value=(mock_chat, MagicMock(), mock_responses, MagicMock()),
        ):
            with patch("code_puppy.model_factory.make_openai_provider"):
                ModelFactory.get_model("gpt-5.6-sol-custom", custom_config)

    mock_chat.assert_not_called()
    mock_responses.assert_called_once_with(model_name="gpt-5.6-sol", provider=ANY)
