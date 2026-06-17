"""Register friendly setup helper tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_first_run_tour as android_first_run_tour_impl,
    android_setup_doctor as android_setup_doctor_impl,
    android_setup_next_steps as android_setup_next_steps_impl,
)

_DOCTOR = "android_setup_doctor"
_NEXT = "android_setup_next_steps"
_TOUR = "android_first_run_tour"



def register_android_setup_doctor(agent: Any) -> None:
    @agent.tool
    async def android_setup_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_setup_doctor_impl()



def register_android_setup_next_steps(agent: Any) -> None:
    @agent.tool
    async def android_setup_next_steps(
        context: RunContext,
        goal: str = "basics",
    ) -> dict[str, Any]:
        del context
        return android_setup_next_steps_impl(goal=goal)



def register_android_first_run_tour(agent: Any) -> None:
    @agent.tool
    async def android_first_run_tour(
        context: RunContext,
        topic: str = "basics",
    ) -> dict[str, Any]:
        del context
        return android_first_run_tour_impl(topic=topic)



def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_setup_doctor},
        {"name": _NEXT, "register_func": register_android_setup_next_steps},
        {"name": _TOUR, "register_func": register_android_first_run_tour},
    ]



def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _NEXT, _TOUR]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
