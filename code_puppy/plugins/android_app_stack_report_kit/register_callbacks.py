"""Register app stack reporting tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_app_stack_report_doctor as android_app_stack_report_doctor_impl,
    android_app_stack_report_examples as android_app_stack_report_examples_impl,
    android_app_stack_report_generate as android_app_stack_report_generate_impl,
)

_DOCTOR = "android_app_stack_report_doctor"
_GENERATE = "android_app_stack_report_generate"
_EXAMPLES = "android_app_stack_report_examples"



def register_android_app_stack_report_doctor(agent: Any) -> None:
    @agent.tool
    async def android_app_stack_report_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_app_stack_report_doctor_impl()



def register_android_app_stack_report_generate(agent: Any) -> None:
    @agent.tool
    async def android_app_stack_report_generate(
        context: RunContext,
        package_names: list[str],
        business_goal: str = "",
        artifact_name: str = "droidpuppy_app_stack_report",
        dry_run: bool = True,
        user: str = "0",
    ) -> dict[str, Any]:
        del context
        return android_app_stack_report_generate_impl(
            package_names=package_names,
            business_goal=business_goal,
            artifact_name=artifact_name,
            dry_run=dry_run,
            user=user,
        )



def register_android_app_stack_report_examples(agent: Any) -> None:
    @agent.tool
    async def android_app_stack_report_examples(context: RunContext) -> dict[str, Any]:
        del context
        return android_app_stack_report_examples_impl()



def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_app_stack_report_doctor},
        {"name": _GENERATE, "register_func": register_android_app_stack_report_generate},
        {"name": _EXAMPLES, "register_func": register_android_app_stack_report_examples},
    ]



def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _GENERATE, _EXAMPLES]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
