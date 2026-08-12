from unittest.mock import patch

from code_puppy.plugins.chatgpt_oauth.utils import add_models_to_extra_config


@patch("code_puppy.plugins.chatgpt_oauth.utils.save_chatgpt_models")
@patch("code_puppy.plugins.chatgpt_oauth.utils.load_chatgpt_models")
def test_add_models_to_extra_config_adds_sol_transport_metadata(mock_load, mock_save):
    mock_load.return_value = {}
    mock_save.return_value = True

    result = add_models_to_extra_config(["gpt-5.6-sol"])

    assert result is True
    saved_config = mock_save.call_args[0][0]
    sol_config = saved_config["codex-gpt-5.6-sol"]
    assert sol_config["type"] == "chatgpt_oauth"
    assert sol_config["name"] == "gpt-5.6-sol"
    assert sol_config["openai_transport"] == "responses"
    assert sol_config["supports_xhigh_reasoning"] is True
    assert sol_config["reasoning_effort_choices"] == [
        "none",
        "low",
        "medium",
        "high",
        "xhigh",
        "max",
    ]
    assert sol_config["supported_settings"] == [
        "reasoning_effort",
        "summary",
        "verbosity",
        "reasoning_context",
        "reasoning_mode",
    ]
