from __future__ import annotations

import configparser
import os
import platform
import sys
from pathlib import Path

RUNTIME_PROFILE_ENV = "CODE_PUPPY_RUNTIME_PROFILE"
_ANDROID_MINIMAL = "android-minimal"
_FULL = "full"
_AUTO = "auto"

_ANDROID_MINIMAL_BUILTIN_PLUGINS = frozenset(
    {
        "destructive_command_guard",
        "file_permission_handler",
        "prompt_newline",
        "puppy_kennel",
        "shell_safety",
    }
)

_ANDROID_MINIMAL_HIDDEN_COMMANDS = frozenset(
    {
        "add_model",
        "mcp",
        "model_settings",
        "reasoning",
        "verbosity",
    }
)

_ANDROID_MINIMAL_HIDDEN_TOOLS = frozenset({"load_image_for_analysis"})


def _xdg_config_dir() -> Path:
    xdg_home = os.environ.get("XDG_CONFIG_HOME", "").strip()
    if xdg_home:
        return Path(xdg_home).expanduser() / "code_puppy"
    return Path.home() / ".code_puppy"


def _config_file_path() -> Path:
    return _xdg_config_dir() / "puppy.cfg"


def _normalize_profile(raw: str | None) -> str:
    value = (raw or "").strip().lower().replace("_", "-")
    if value in {"", _AUTO}:
        return _AUTO
    if value in {"minimal", "lean", "android-minimal", "android-lean"}:
        return _ANDROID_MINIMAL
    if value in {_FULL, "default"}:
        return _FULL
    return _AUTO


def detect_runtime_environment() -> dict[str, bool]:
    executable = Path(sys.executable).expanduser()
    release = platform.release().lower()
    system_name = platform.system()
    prefix = os.environ.get("PREFIX", "")
    termux_version = os.environ.get("TERMUX_VERSION", "")
    is_termux = (
        bool(termux_version)
        or "com.termux" in str(executable)
        or (system_name == "Linux" and "com.termux" in prefix)
    )
    is_android = is_termux or "android" in release
    return {"is_android": is_android, "is_termux": is_termux}


def _config_runtime_profile() -> str:
    config_path = _config_file_path()
    if not config_path.exists():
        return _AUTO

    parser = configparser.ConfigParser()
    try:
        parser.read(config_path, encoding="utf-8")
    except Exception:
        return _AUTO

    if not parser.has_section("puppy"):
        return _AUTO
    return _normalize_profile(parser.get("puppy", "runtime_profile", fallback="auto"))


def get_runtime_profile() -> str:
    """Resolve the active runtime profile.

    Android/Termux defaults to ``android-minimal`` so a lean installation does
    not eagerly load desktop-oriented built-ins or the full model inventory.
    User and project overlays remain separately discoverable, and operators can
    explicitly select ``full`` via environment or config when needed.
    """
    env_choice = _normalize_profile(os.environ.get(RUNTIME_PROFILE_ENV))
    if env_choice != _AUTO:
        return env_choice

    config_choice = _config_runtime_profile()
    if config_choice != _AUTO:
        return config_choice

    environment = detect_runtime_environment()
    if environment["is_android"]:
        return _ANDROID_MINIMAL
    return _FULL


def allowed_builtin_plugins_for_runtime(profile: str | None = None) -> set[str] | None:
    resolved = (
        _normalize_profile(profile) if profile is not None else get_runtime_profile()
    )
    if resolved == _ANDROID_MINIMAL:
        return set(_ANDROID_MINIMAL_BUILTIN_PLUGINS)
    return None


def hidden_command_names_for_runtime(profile: str | None = None) -> set[str]:
    resolved = (
        _normalize_profile(profile) if profile is not None else get_runtime_profile()
    )
    if resolved == _ANDROID_MINIMAL:
        return set(_ANDROID_MINIMAL_HIDDEN_COMMANDS)
    return set()


def command_visible_in_runtime(command_name: str, profile: str | None = None) -> bool:
    return command_name not in hidden_command_names_for_runtime(profile)


def hidden_tool_names_for_runtime(profile: str | None = None) -> set[str]:
    resolved = (
        _normalize_profile(profile) if profile is not None else get_runtime_profile()
    )
    if resolved == _ANDROID_MINIMAL:
        return set(_ANDROID_MINIMAL_HIDDEN_TOOLS)
    return set()


def bundled_models_path(
    base_dir: Path | None = None, profile: str | None = None
) -> Path:
    root = base_dir or Path(__file__).parent
    resolved = (
        _normalize_profile(profile) if profile is not None else get_runtime_profile()
    )
    if resolved == _ANDROID_MINIMAL:
        return root / "models_minimal.json"
    return root / "models.json"
