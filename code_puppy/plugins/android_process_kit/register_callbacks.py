"""Register Android process kit tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_process_doctor as android_process_doctor_impl,
    android_process_list as android_process_list_impl,
    android_top_snapshot as android_top_snapshot_impl,
)

_DOCTOR = "android_process_doctor"
_LIST = "android_process_list"
_TOP = "android_top_snapshot"


def register_android_process_doctor(agent: Any) -> None:
    @agent.tool
    async def android_process_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_process_doctor_impl()


def register_android_process_list(agent: Any) -> None:
    @agent.tool
    async def android_process_list(
        context: RunContext,
        query: str = "",
        max_results: int = 100,
    ) -> dict[str, Any]:
        del context
        return android_process_list_impl(query=query, max_results=max_results)


def register_android_top_snapshot(agent: Any) -> None:
    @agent.tool
    async def android_top_snapshot(
        context: RunContext,
        query: str = "",
        max_lines: int = 80,
    ) -> dict[str, Any]:
        del context
        return android_top_snapshot_impl(query=query, max_lines=max_lines)


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_process_doctor},
        {"name": _LIST, "register_func": register_android_process_list},
        {"name": _TOP, "register_func": register_android_top_snapshot},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _LIST, _TOP]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
