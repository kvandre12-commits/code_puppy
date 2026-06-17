"""Register Android bugreport kit tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_bugreport_collect as android_bugreport_collect_impl,
    android_bugreport_doctor as android_bugreport_doctor_impl,
)

_DOCTOR = "android_bugreport_doctor"
_COLLECT = "android_bugreport_collect"



def register_android_bugreport_doctor(agent: Any) -> None:
    @agent.tool
    async def android_bugreport_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_bugreport_doctor_impl()



def register_android_bugreport_collect(agent: Any) -> None:
    @agent.tool
    async def android_bugreport_collect(
        context: RunContext,
        artifact_name: str = "android_bugreport",
        dry_run: bool = True,
        timeout_seconds: int = 900,
    ) -> dict[str, Any]:
        del context
        return android_bugreport_collect_impl(
            artifact_name=artifact_name,
            dry_run=dry_run,
            timeout_seconds=timeout_seconds,
        )



def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_bugreport_doctor},
        {"name": _COLLECT, "register_func": register_android_bugreport_collect},
    ]



def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _COLLECT]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
