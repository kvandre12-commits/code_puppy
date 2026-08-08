from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    _TOOL_SIGN_REQUEST,
    _TOOL_STATUS,
    _TOOL_WRITE_CONFIG,
    advertise_tools,
    custom_help,
    handle_custom_command,
    private_operator_channel_sign_request as sign_request_impl,
    private_operator_channel_status as status_impl,
    private_operator_channel_write_example_config as write_config_impl,
)


def register_private_operator_channel_status(agent: Any) -> None:
    @agent.tool
    async def private_operator_channel_status(
        context: RunContext,
        config_path: str = "",
        include_authority: bool = True,
        include_bus: bool = True,
    ) -> dict[str, Any]:
        del context
        return status_impl(
            config_path=config_path,
            include_authority=include_authority,
            include_bus=include_bus,
        )


def register_private_operator_channel_write_example_config(agent: Any) -> None:
    @agent.tool
    async def private_operator_channel_write_example_config(
        context: RunContext,
        output_path: str = "",
        overwrite: bool = False,
    ) -> dict[str, Any]:
        del context
        return write_config_impl(output_path=output_path, overwrite=overwrite)


def register_private_operator_channel_sign_request(agent: Any) -> None:
    @agent.tool
    async def private_operator_channel_sign_request(
        context: RunContext,
        action: str,
        args_json: str = "{}",
        shared_secret: str = "",
        secret_env: str = "PRIVATE_OPERATOR_CHANNEL_SECRET",
        output_path: str = "",
    ) -> dict[str, Any]:
        del context
        return sign_request_impl(
            action=action,
            args_json=args_json,
            shared_secret=shared_secret,
            secret_env=secret_env,
            output_path=output_path,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _TOOL_STATUS, "register_func": register_private_operator_channel_status},
        {
            "name": _TOOL_WRITE_CONFIG,
            "register_func": register_private_operator_channel_write_example_config,
        },
        {
            "name": _TOOL_SIGN_REQUEST,
            "register_func": register_private_operator_channel_sign_request,
        },
    ]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", advertise_tools)
register_callback("custom_command_help", custom_help)
register_callback("custom_command", handle_custom_command)
