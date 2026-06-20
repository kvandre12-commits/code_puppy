"""Register wireless ADB reconnect helper tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_reconnect_doctor as android_reconnect_doctor_impl,
    android_reconnect_full as android_reconnect_full_impl,
    android_reconnect_plan as android_reconnect_plan_impl,
    android_reconnect_quick as android_reconnect_quick_impl,
)

_DOCTOR = "android_reconnect_doctor"
_PLAN = "android_reconnect_plan"
_QUICK = "android_reconnect_quick"
_FULL = "android_reconnect_full"


def register_android_reconnect_doctor(agent: Any) -> None:
    @agent.tool
    async def android_reconnect_doctor(
        context: RunContext,
        host: str = "",
        connect_port: int = 0,
    ) -> dict[str, Any]:
        del context
        return android_reconnect_doctor_impl(host=host, connect_port=connect_port)


def register_android_reconnect_plan(agent: Any) -> None:
    @agent.tool
    async def android_reconnect_plan(
        context: RunContext,
        host: str,
        connect_port: int,
        pair_port: int = 0,
        pair_code: str = "",
    ) -> dict[str, Any]:
        del context
        return android_reconnect_plan_impl(
            host=host,
            connect_port=connect_port,
            pair_port=pair_port,
            pair_code=pair_code,
        )


def register_android_reconnect_quick(agent: Any) -> None:
    @agent.tool
    async def android_reconnect_quick(
        context: RunContext,
        host: str,
        connect_port: int,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return android_reconnect_quick_impl(
            host=host,
            connect_port=connect_port,
            dry_run=dry_run,
        )


def register_android_reconnect_full(agent: Any) -> None:
    @agent.tool
    async def android_reconnect_full(
        context: RunContext,
        host: str,
        pair_port: int,
        pair_code: str,
        connect_port: int,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return android_reconnect_full_impl(
            host=host,
            pair_port=pair_port,
            pair_code=pair_code,
            connect_port=connect_port,
            dry_run=dry_run,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_reconnect_doctor},
        {"name": _PLAN, "register_func": register_android_reconnect_plan},
        {"name": _QUICK, "register_func": register_android_reconnect_quick},
        {"name": _FULL, "register_func": register_android_reconnect_full},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _PLAN, _QUICK, _FULL]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
