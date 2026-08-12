"""Register Android paginated crawl helper tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_paginated_crawl_doctor as android_paginated_crawl_doctor_impl,
    android_paginated_crawl_examples as android_paginated_crawl_examples_impl,
    android_paginated_crawl_run as android_paginated_crawl_run_impl,
)

_DOCTOR = "android_paginated_crawl_doctor"
_EXAMPLES = "android_paginated_crawl_examples"
_RUN = "android_paginated_crawl_run"


def register_android_paginated_crawl_doctor(agent: Any) -> None:
    @agent.tool
    async def android_paginated_crawl_doctor(
        context: RunContext,
    ) -> dict[str, Any]:
        del context
        return android_paginated_crawl_doctor_impl()


def register_android_paginated_crawl_examples(agent: Any) -> None:
    @agent.tool
    async def android_paginated_crawl_examples(
        context: RunContext,
    ) -> dict[str, Any]:
        del context
        return android_paginated_crawl_examples_impl()


def register_android_paginated_crawl_run(agent: Any) -> None:
    @agent.tool
    async def android_paginated_crawl_run(
        context: RunContext,
        plan_json: str,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return android_paginated_crawl_run_impl(plan_json=plan_json, dry_run=dry_run)


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_android_paginated_crawl_doctor},
        {"name": _EXAMPLES, "register_func": register_android_paginated_crawl_examples},
        {"name": _RUN, "register_func": register_android_paginated_crawl_run},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR, _EXAMPLES, _RUN]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
