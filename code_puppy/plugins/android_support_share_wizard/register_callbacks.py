"""Register support bundle sharing and issue-draft tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_support_bundle_list as android_support_bundle_list_impl,
    android_support_bundle_summarize as android_support_bundle_summarize_impl,
    android_support_issue_draft as android_support_issue_draft_impl,
    android_support_share_wizard as android_support_share_wizard_impl,
)

_LIST = "android_support_bundle_list"
_SUMMARIZE = "android_support_bundle_summarize"
_DRAFT = "android_support_issue_draft"
_SHARE = "android_support_share_wizard"



def register_android_support_bundle_list(agent: Any) -> None:
    @agent.tool
    async def android_support_bundle_list(
        context: RunContext,
        max_results: int = 10,
    ) -> dict[str, Any]:
        del context
        return android_support_bundle_list_impl(max_results=max_results)



def register_android_support_bundle_summarize(agent: Any) -> None:
    @agent.tool
    async def android_support_bundle_summarize(
        context: RunContext,
        bundle_path: str = "",
    ) -> dict[str, Any]:
        del context
        return android_support_bundle_summarize_impl(bundle_path=bundle_path)



def register_android_support_issue_draft(agent: Any) -> None:
    @agent.tool
    async def android_support_issue_draft(
        context: RunContext,
        bundle_path: str = "",
        artifact_name: str = "droidpuppy_support_issue",
    ) -> dict[str, Any]:
        del context
        return android_support_issue_draft_impl(
            bundle_path=bundle_path,
            artifact_name=artifact_name,
        )



def register_android_support_share_wizard(agent: Any) -> None:
    @agent.tool
    async def android_support_share_wizard(
        context: RunContext,
        bundle_path: str = "",
        recipient_hint: str = "",
        share_now: bool = False,
    ) -> dict[str, Any]:
        del context
        return android_support_share_wizard_impl(
            bundle_path=bundle_path,
            recipient_hint=recipient_hint,
            share_now=share_now,
        )



def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _LIST, "register_func": register_android_support_bundle_list},
        {"name": _SUMMARIZE, "register_func": register_android_support_bundle_summarize},
        {"name": _DRAFT, "register_func": register_android_support_issue_draft},
        {"name": _SHARE, "register_func": register_android_support_share_wizard},
    ]



def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_LIST, _SUMMARIZE, _DRAFT, _SHARE]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
