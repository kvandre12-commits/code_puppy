"""Register named cross-app workflow tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_app_workflow_doctor as android_app_workflow_doctor_impl,
    android_app_workflow_list as android_app_workflow_list_impl,
    android_app_workflow_run as android_app_workflow_run_impl,
)

_DOCTOR = "android_app_workflow_doctor"
_LIST = "android_app_workflow_list"
_RUN = "android_app_workflow_run"


def register_android_app_workflow_doctor(agent: Any) -> None:
    @agent.tool
    async def android_app_workflow_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_app_workflow_doctor_impl()


def register_android_app_workflow_list(agent: Any) -> None:
    @agent.tool
    async def android_app_workflow_list(context: RunContext) -> dict[str, Any]:
        del context
        return android_app_workflow_list_impl()


def register_android_app_workflow_run(agent: Any) -> None:
    @agent.tool
    async def android_app_workflow_run(
        context: RunContext,
        name: str,
        dry_run: bool = True,
        repo_url: str = "https://github.com/kvandre12-commits/DroidPuppy",
        artifact_name: str = "droidpuppy_workflow_support_bundle",
        recipient_hint: str = "",
    ) -> dict[str, Any]:
        del context
        return android_app_workflow_run_impl(
            name=name,
            dry_run=dry_run,
            repo_url=repo_url,
            artifact_name=artifact_name,
            recipient_hint=recipient_hint,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_app_workflow_doctor},
        {"name": _LIST, "register_func": register_android_app_workflow_list},
        {"name": _RUN, "register_func": register_android_app_workflow_run},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _LIST, _RUN]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
