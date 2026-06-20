"""Register UI capability audit tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_ui_capability_audit_app as android_ui_capability_audit_app_impl,
    android_ui_capability_audit_doctor as android_ui_capability_audit_doctor_impl,
    android_ui_capability_audit_examples as android_ui_capability_audit_examples_impl,
    android_ui_capability_audit_stack as android_ui_capability_audit_stack_impl,
)

_DOCTOR = "android_ui_capability_audit_doctor"
_APP = "android_ui_capability_audit_app"
_STACK = "android_ui_capability_audit_stack"
_EXAMPLES = "android_ui_capability_audit_examples"


def register_android_ui_capability_audit_doctor(agent: Any) -> None:
    @agent.tool
    async def android_ui_capability_audit_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_ui_capability_audit_doctor_impl()


def register_android_ui_capability_audit_app(agent: Any) -> None:
    @agent.tool
    async def android_ui_capability_audit_app(
        context: RunContext,
        package_name: str,
        user: str = "0",
    ) -> dict[str, Any]:
        del context
        return android_ui_capability_audit_app_impl(
            package_name=package_name, user=user
        )


def register_android_ui_capability_audit_stack(agent: Any) -> None:
    @agent.tool
    async def android_ui_capability_audit_stack(
        context: RunContext,
        package_names: list[str],
        user: str = "0",
    ) -> dict[str, Any]:
        del context
        return android_ui_capability_audit_stack_impl(
            package_names=package_names, user=user
        )


def register_android_ui_capability_audit_examples(agent: Any) -> None:
    @agent.tool
    async def android_ui_capability_audit_examples(
        context: RunContext,
    ) -> dict[str, Any]:
        del context
        return android_ui_capability_audit_examples_impl()


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_ui_capability_audit_doctor},
        {"name": _APP, "register_func": register_android_ui_capability_audit_app},
        {"name": _STACK, "register_func": register_android_ui_capability_audit_stack},
        {
            "name": _EXAMPLES,
            "register_func": register_android_ui_capability_audit_examples,
        },
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _APP, _STACK, _EXAMPLES]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
