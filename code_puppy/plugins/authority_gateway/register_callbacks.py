from __future__ import annotations

from typing import Any

from code_puppy.callbacks import register_callback

from .policy import build_pre_tool_response, handle_post_tool_result


async def on_pre_tool_call(
    tool_name: str, tool_args: dict[str, Any], context: Any = None
) -> dict[str, Any] | None:
    del context
    return build_pre_tool_response(tool_name, tool_args)


async def on_post_tool_call(
    tool_name: str,
    tool_args: dict[str, Any],
    result: Any,
    duration_ms: float,
    context: Any = None,
) -> None:
    del tool_args, duration_ms, context
    handle_post_tool_result(tool_name, result)


register_callback("pre_tool_call", on_pre_tool_call)
register_callback("post_tool_call", on_post_tool_call)
