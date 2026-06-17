"""Register workflow feasibility assessment tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_workflow_feasibility_assess as android_workflow_feasibility_assess_impl,
    android_workflow_feasibility_doctor as android_workflow_feasibility_doctor_impl,
    android_workflow_feasibility_examples as android_workflow_feasibility_examples_impl,
)

_DOCTOR = "android_workflow_feasibility_doctor"
_ASSESS = "android_workflow_feasibility_assess"
_EXAMPLES = "android_workflow_feasibility_examples"



def register_android_workflow_feasibility_doctor(agent: Any) -> None:
    @agent.tool
    async def android_workflow_feasibility_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_workflow_feasibility_doctor_impl()



def register_android_workflow_feasibility_assess(agent: Any) -> None:
    @agent.tool
    async def android_workflow_feasibility_assess(
        context: RunContext,
        package_names: list[str],
        business_goal: str = "",
        user: str = "0",
    ) -> dict[str, Any]:
        del context
        return android_workflow_feasibility_assess_impl(
            package_names=package_names,
            business_goal=business_goal,
            user=user,
        )



def register_android_workflow_feasibility_examples(agent: Any) -> None:
    @agent.tool
    async def android_workflow_feasibility_examples(context: RunContext) -> dict[str, Any]:
        del context
        return android_workflow_feasibility_examples_impl()



def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_workflow_feasibility_doctor},
        {"name": _ASSESS, "register_func": register_android_workflow_feasibility_assess},
        {"name": _EXAMPLES, "register_func": register_android_workflow_feasibility_examples},
    ]



def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _ASSESS, _EXAMPLES]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
