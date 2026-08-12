"""Register the quiet DroidPuppy hygiene worker."""

from __future__ import annotations

from typing import Any

from code_puppy.callbacks import register_callback

from .state import format_report, record_checkpoint, record_tool_call

_COMMAND = "hygiene"


def _emit_info(message: str) -> None:
    try:
        from code_puppy.messaging import emit_info

        emit_info(message)
    except Exception:
        print(message)


def _post_tool_call(
    tool_name: str,
    tool_args: dict[str, Any] | None,
    result: Any,
    duration_ms: int | float | None,
    context: Any = None,
) -> None:
    del context
    try:
        record_tool_call(tool_name, tool_args or {}, result, duration_ms)
    except Exception:
        # Hygiene must never interrupt the work. Quiet means quiet.
        return None
    return None


def _interactive_turn_end(*args: Any, **kwargs: Any) -> None:
    del args, kwargs
    try:
        record_checkpoint("interactive_turn_end")
    except Exception:
        return None
    return None


def _pre_compact(*args: Any, **kwargs: Any) -> None:
    del args, kwargs
    try:
        record_checkpoint("pre_compact")
    except Exception:
        return None
    return None


def _session_end(*args: Any, **kwargs: Any) -> None:
    del args, kwargs
    try:
        record_checkpoint("session_end")
    except Exception:
        return None
    return None


def _custom_help() -> list[tuple[str, str]]:
    return [(_COMMAND, "Show the quiet DroidPuppy hygiene packet")]


def _custom_command(command: str, name: str):
    del command
    if name != _COMMAND:
        return None
    try:
        state = record_checkpoint("manual_hygiene_report")
        _emit_info(format_report(state))
    except Exception as exc:
        _emit_info(f"DroidPuppy hygiene worker unavailable: {exc}")
    return True


register_callback("post_tool_call", _post_tool_call)
register_callback("interactive_turn_end", _interactive_turn_end)
register_callback("pre_compact", _pre_compact)
register_callback("session_end", _session_end)
register_callback("custom_command_help", _custom_help)
register_callback("custom_command", _custom_command)
