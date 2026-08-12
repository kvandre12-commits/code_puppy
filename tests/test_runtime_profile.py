from __future__ import annotations

from pathlib import Path

from code_puppy.runtime_profile import (
    allowed_builtin_plugins_for_runtime,
    bundled_models_path,
    command_visible_in_runtime,
    detect_runtime_environment,
    get_runtime_profile,
    hidden_command_names_for_runtime,
    hidden_tool_names_for_runtime,
)


def test_detect_runtime_environment_termux(monkeypatch):
    monkeypatch.setenv("TERMUX_VERSION", "0.119")
    monkeypatch.setenv("PREFIX", "/data/data/com.termux/files/usr")
    environment = detect_runtime_environment()
    assert environment["is_termux"] is True
    assert environment["is_android"] is True


def test_get_runtime_profile_prefers_env_override(monkeypatch):
    monkeypatch.setenv("TERMUX_VERSION", "0.119")
    monkeypatch.setenv("PREFIX", "/data/data/com.termux/files/usr")
    monkeypatch.setenv("CODE_PUPPY_RUNTIME_PROFILE", "full")
    assert get_runtime_profile() == "full"


def test_get_runtime_profile_reads_config_override(tmp_path, monkeypatch):
    config_dir = tmp_path / "xdg-config"
    puppy_dir = config_dir / "code_puppy"
    puppy_dir.mkdir(parents=True)
    (puppy_dir / "puppy.cfg").write_text(
        "[puppy]\nruntime_profile = minimal\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("CODE_PUPPY_RUNTIME_PROFILE", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
    assert get_runtime_profile() == "android-minimal"


def test_allowed_builtin_plugins_for_android_minimal_contains_core_guardrails():
    allowed = allowed_builtin_plugins_for_runtime("android-minimal")
    assert allowed is not None
    assert "destructive_command_guard" in allowed
    assert "file_permission_handler" in allowed
    assert "puppy_kennel" in allowed
    assert "chatgpt_oauth" not in allowed
    assert "claude_code_oauth" not in allowed
    assert "agent_skills" not in allowed


def test_android_minimal_runtime_hides_optional_command_surface():
    hidden = hidden_command_names_for_runtime("android-minimal")
    assert "mcp" in hidden
    assert "add_model" in hidden
    assert "model_settings" in hidden
    assert command_visible_in_runtime("help", profile="android-minimal") is True
    assert command_visible_in_runtime("mcp", profile="android-minimal") is False


def test_android_minimal_runtime_hides_optional_tool_surface():
    hidden = hidden_tool_names_for_runtime("android-minimal")
    assert hidden == {"load_image_for_analysis"}
    assert hidden_tool_names_for_runtime("full") == set()


def test_bundled_models_path_switches_with_profile():
    base_dir = Path("/tmp/code-puppy-test")
    assert (
        bundled_models_path(base_dir, profile="android-minimal").name
        == "models_minimal.json"
    )
    assert bundled_models_path(base_dir, profile="full").name == "models.json"
