"""Register structured Android intent tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_intent_build as android_intent_build_impl,
    android_intent_doctor as android_intent_doctor_impl,
    android_intent_examples as android_intent_examples_impl,
    android_intent_send as android_intent_send_impl,
)

_DOCTOR = "android_intent_doctor"
_BUILD = "android_intent_build"
_SEND = "android_intent_send"
_EXAMPLES = "android_intent_examples"


def register_android_intent_doctor(agent: Any) -> None:
    @agent.tool
    async def android_intent_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return android_intent_doctor_impl()


def register_android_intent_build(agent: Any) -> None:
    @agent.tool
    async def android_intent_build(
        context: RunContext,
        action: str = "",
        data_uri: str = "",
        mime_type: str = "",
        package_name: str = "",
        activity_name: str = "",
        categories: list[str] | None = None,
        string_extras: dict[str, str] | None = None,
        bool_extras: dict[str, bool] | None = None,
        int_extras: dict[str, int] | None = None,
        long_extras: dict[str, int] | None = None,
        float_extras: dict[str, float] | None = None,
        flags: list[str] | None = None,
        chooser_title: str = "",
        dispatch_mode: str = "start",
    ) -> dict[str, Any]:
        del context
        return android_intent_build_impl(
            action=action,
            data_uri=data_uri,
            mime_type=mime_type,
            package_name=package_name,
            activity_name=activity_name,
            categories=categories,
            string_extras=string_extras,
            bool_extras=bool_extras,
            int_extras=int_extras,
            long_extras=long_extras,
            float_extras=float_extras,
            flags=flags,
            chooser_title=chooser_title,
            dispatch_mode=dispatch_mode,
        )


def register_android_intent_send(agent: Any) -> None:
    @agent.tool
    async def android_intent_send(
        context: RunContext,
        action: str = "",
        data_uri: str = "",
        mime_type: str = "",
        package_name: str = "",
        activity_name: str = "",
        categories: list[str] | None = None,
        string_extras: dict[str, str] | None = None,
        bool_extras: dict[str, bool] | None = None,
        int_extras: dict[str, int] | None = None,
        long_extras: dict[str, int] | None = None,
        float_extras: dict[str, float] | None = None,
        flags: list[str] | None = None,
        chooser_title: str = "",
        dispatch_mode: str = "start",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return android_intent_send_impl(
            action=action,
            data_uri=data_uri,
            mime_type=mime_type,
            package_name=package_name,
            activity_name=activity_name,
            categories=categories,
            string_extras=string_extras,
            bool_extras=bool_extras,
            int_extras=int_extras,
            long_extras=long_extras,
            float_extras=float_extras,
            flags=flags,
            chooser_title=chooser_title,
            dispatch_mode=dispatch_mode,
            dry_run=dry_run,
        )


def register_android_intent_examples(agent: Any) -> None:
    @agent.tool
    async def android_intent_examples(context: RunContext) -> dict[str, Any]:
        del context
        return android_intent_examples_impl()


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_intent_doctor},
        {"name": _BUILD, "register_func": register_android_intent_build},
        {"name": _SEND, "register_func": register_android_intent_send},
        {"name": _EXAMPLES, "register_func": register_android_intent_examples},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _BUILD, _SEND, _EXAMPLES]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
