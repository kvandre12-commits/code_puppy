"""Register Android handoff tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_handoff_doctor as android_handoff_doctor_impl,
    android_handoff_examples as android_handoff_examples_impl,
    android_handoff_file as android_handoff_file_impl,
    android_handoff_text as android_handoff_text_impl,
    android_handoff_url as android_handoff_url_impl,
)

_DOCTOR = "android_handoff_doctor"
_TEXT = "android_handoff_text"
_URL = "android_handoff_url"
_FILE = "android_handoff_file"
_EXAMPLES = "android_handoff_examples"



def register_android_handoff_doctor(agent: Any) -> None:
    @agent.tool
    async def android_handoff_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_handoff_doctor_impl()



def register_android_handoff_text(agent: Any) -> None:
    @agent.tool
    async def android_handoff_text(
        context: RunContext,
        text: str,
        subject: str = "",
        package_name: str = "",
        chooser_title: str = "",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return android_handoff_text_impl(
            text=text,
            subject=subject,
            package_name=package_name,
            chooser_title=chooser_title,
            dry_run=dry_run,
        )



def register_android_handoff_url(agent: Any) -> None:
    @agent.tool
    async def android_handoff_url(
        context: RunContext,
        url: str,
        package_name: str = "",
        chooser_title: str = "",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return android_handoff_url_impl(
            url=url,
            package_name=package_name,
            chooser_title=chooser_title,
            dry_run=dry_run,
        )



def register_android_handoff_file(agent: Any) -> None:
    @agent.tool
    async def android_handoff_file(
        context: RunContext,
        file_path: str,
        send: bool = True,
        chooser: bool = False,
        content_type: str = "",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return android_handoff_file_impl(
            file_path=file_path,
            send=send,
            chooser=chooser,
            content_type=content_type,
            dry_run=dry_run,
        )



def register_android_handoff_examples(agent: Any) -> None:
    @agent.tool
    async def android_handoff_examples(context: RunContext) -> dict[str, Any]:
        del context
        return android_handoff_examples_impl()



def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_handoff_doctor},
        {"name": _TEXT, "register_func": register_android_handoff_text},
        {"name": _URL, "register_func": register_android_handoff_url},
        {"name": _FILE, "register_func": register_android_handoff_file},
        {"name": _EXAMPLES, "register_func": register_android_handoff_examples},
    ]



def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _TEXT, _URL, _FILE, _EXAMPLES]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
