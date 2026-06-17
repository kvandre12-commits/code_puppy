"""Register Android dumpsys kit tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_dumpsys_doctor as android_dumpsys_doctor_impl,
    android_dumpsys_service as android_dumpsys_service_impl,
    android_dumpsys_snapshot as android_dumpsys_snapshot_impl,
)

_DOCTOR = "android_dumpsys_doctor"
_SERVICE = "android_dumpsys_service"
_SNAPSHOT = "android_dumpsys_snapshot"



def register_android_dumpsys_doctor(agent: Any) -> None:
    @agent.tool
    async def android_dumpsys_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_dumpsys_doctor_impl()



def register_android_dumpsys_service(agent: Any) -> None:
    @agent.tool
    async def android_dumpsys_service(
        context: RunContext,
        service: str,
        contains: str = "",
        max_chars: int = 12000,
    ) -> dict[str, Any]:
        del context
        return android_dumpsys_service_impl(
            service=service,
            contains=contains,
            max_chars=max_chars,
        )



def register_android_dumpsys_snapshot(agent: Any) -> None:
    @agent.tool
    async def android_dumpsys_snapshot(
        context: RunContext,
        max_chars_per_service: int = 4000,
    ) -> dict[str, Any]:
        del context
        return android_dumpsys_snapshot_impl(max_chars_per_service=max_chars_per_service)



def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_dumpsys_doctor},
        {"name": _SERVICE, "register_func": register_android_dumpsys_service},
        {"name": _SNAPSHOT, "register_func": register_android_dumpsys_snapshot},
    ]



def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _SERVICE, _SNAPSHOT]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
