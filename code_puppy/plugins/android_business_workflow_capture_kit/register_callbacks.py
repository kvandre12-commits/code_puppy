"""Register business workflow capture tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_business_workflow_capture_create as android_business_workflow_capture_create_impl,
    android_business_workflow_capture_doctor as android_business_workflow_capture_doctor_impl,
    android_business_workflow_capture_examples as android_business_workflow_capture_examples_impl,
    android_business_workflow_capture_template as android_business_workflow_capture_template_impl,
)

_DOCTOR = "android_business_workflow_capture_doctor"
_TEMPLATE = "android_business_workflow_capture_template"
_CREATE = "android_business_workflow_capture_create"
_EXAMPLES = "android_business_workflow_capture_examples"



def register_android_business_workflow_capture_doctor(agent: Any) -> None:
    @agent.tool
    async def android_business_workflow_capture_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_business_workflow_capture_doctor_impl()



def register_android_business_workflow_capture_template(agent: Any) -> None:
    @agent.tool
    async def android_business_workflow_capture_template(
        context: RunContext,
        industry: str = "retail",
    ) -> dict[str, Any]:
        del context
        return android_business_workflow_capture_template_impl(industry=industry)



def register_android_business_workflow_capture_create(agent: Any) -> None:
    @agent.tool
    async def android_business_workflow_capture_create(
        context: RunContext,
        workflow_name: str,
        business_goal: str,
        package_names: list[str],
        current_steps: list[str],
        pain_points: list[str],
        success_criteria: list[str],
        business_name: str = "",
        industry: str = "general",
        artifact_name: str = "droidpuppy_business_workflow",
        dry_run: bool = True,
        user: str = "0",
    ) -> dict[str, Any]:
        del context
        return android_business_workflow_capture_create_impl(
            workflow_name=workflow_name,
            business_goal=business_goal,
            package_names=package_names,
            current_steps=current_steps,
            pain_points=pain_points,
            success_criteria=success_criteria,
            business_name=business_name,
            industry=industry,
            artifact_name=artifact_name,
            dry_run=dry_run,
            user=user,
        )



def register_android_business_workflow_capture_examples(agent: Any) -> None:
    @agent.tool
    async def android_business_workflow_capture_examples(context: RunContext) -> dict[str, Any]:
        del context
        return android_business_workflow_capture_examples_impl()



def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_business_workflow_capture_doctor},
        {"name": _TEMPLATE, "register_func": register_android_business_workflow_capture_template},
        {"name": _CREATE, "register_func": register_android_business_workflow_capture_create},
        {"name": _EXAMPLES, "register_func": register_android_business_workflow_capture_examples},
    ]



def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _TEMPLATE, _CREATE, _EXAMPLES]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
