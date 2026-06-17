"""Register the Android App Doctor tool."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import android_app_doctor as android_app_doctor_impl

_DOCTOR = "android_app_doctor"


def register_android_app_doctor(agent: Any) -> None:
    @agent.tool
    async def android_app_doctor(
        context: RunContext,
        package: str = "",
        lines: int = 4000,
        use_adb: bool = True,
        log_text: str = "",
    ) -> dict[str, Any]:
        del context
        return android_app_doctor_impl(
            package=package,
            lines=lines,
            use_adb=use_adb,
            log_text=log_text,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    return [{"name": _DOCTOR, "register_func": register_android_app_doctor}]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
