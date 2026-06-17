"""Register orchestration blueprint tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_orchestration_blueprint_doctor as android_orchestration_blueprint_doctor_impl,
    android_orchestration_blueprint_examples as android_orchestration_blueprint_examples_impl,
    android_orchestration_blueprint_plan as android_orchestration_blueprint_plan_impl,
)

_DOCTOR = "android_orchestration_blueprint_doctor"
_PLAN = "android_orchestration_blueprint_plan"
_EXAMPLES = "android_orchestration_blueprint_examples"



def register_android_orchestration_blueprint_doctor(agent: Any) -> None:
    @agent.tool
    async def android_orchestration_blueprint_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_orchestration_blueprint_doctor_impl()



def register_android_orchestration_blueprint_plan(agent: Any) -> None:
    @agent.tool
    async def android_orchestration_blueprint_plan(
        context: RunContext,
        package_names: list[str],
        business_goal: str = "",
        artifact_name: str = "droidpuppy_orchestration_blueprint",
        dry_run: bool = True,
        user: str = "0",
    ) -> dict[str, Any]:
        del context
        return android_orchestration_blueprint_plan_impl(
            package_names=package_names,
            business_goal=business_goal,
            artifact_name=artifact_name,
            dry_run=dry_run,
            user=user,
        )



def register_android_orchestration_blueprint_examples(agent: Any) -> None:
    @agent.tool
    async def android_orchestration_blueprint_examples(context: RunContext) -> dict[str, Any]:
        del context
        return android_orchestration_blueprint_examples_impl()



def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_orchestration_blueprint_doctor},
        {"name": _PLAN, "register_func": register_android_orchestration_blueprint_plan},
        {"name": _EXAMPLES, "register_func": register_android_orchestration_blueprint_examples},
    ]



def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _PLAN, _EXAMPLES]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
