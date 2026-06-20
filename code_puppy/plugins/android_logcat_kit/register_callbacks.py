"""Register Android logcat kit tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_logcat_clear as android_logcat_clear_impl,
    android_logcat_doctor as android_logcat_doctor_impl,
    android_logcat_recent as android_logcat_recent_impl,
)

_DOCTOR = "android_logcat_doctor"
_RECENT = "android_logcat_recent"
_CLEAR = "android_logcat_clear"


def register_android_logcat_doctor(agent: Any) -> None:
    @agent.tool
    async def android_logcat_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_logcat_doctor_impl()


def register_android_logcat_recent(agent: Any) -> None:
    @agent.tool
    async def android_logcat_recent(
        context: RunContext,
        lines: int = 200,
        use_adb: bool = True,
        format: str = "threadtime",
        priority: str = "",
        contains: str = "",
        max_chars: int = 12000,
    ) -> dict[str, Any]:
        del context
        return android_logcat_recent_impl(
            lines=lines,
            use_adb=use_adb,
            format=format,
            priority=priority,
            contains=contains,
            max_chars=max_chars,
        )


def register_android_logcat_clear(agent: Any) -> None:
    @agent.tool
    async def android_logcat_clear(
        context: RunContext,
        use_adb: bool = True,
    ) -> dict[str, Any]:
        del context
        return android_logcat_clear_impl(use_adb=use_adb)


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_logcat_doctor},
        {"name": _RECENT, "register_func": register_android_logcat_recent},
        {"name": _CLEAR, "register_func": register_android_logcat_clear},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _RECENT, _CLEAR]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
