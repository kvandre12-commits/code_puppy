"""Register read-only SEC/EDGAR tools with Code Puppy."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    sec_edgar_company_facts as company_facts_impl,
    sec_edgar_company_profile as company_profile_impl,
    sec_edgar_recent_filings as recent_filings_impl,
)

_TOOL_NAMES = (
    "sec_edgar_company_profile",
    "sec_edgar_recent_filings",
    "sec_edgar_company_facts",
)


def register_company_profile(agent: Any) -> None:
    @agent.tool
    async def sec_edgar_company_profile(
        context: RunContext, ticker: str
    ) -> dict[str, Any]:
        del context
        return company_profile_impl(ticker)


def register_recent_filings(agent: Any) -> None:
    @agent.tool
    async def sec_edgar_recent_filings(
        context: RunContext,
        ticker: str,
        forms: list[str] | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        del context
        return recent_filings_impl(ticker, forms=forms, limit=limit)


def register_company_facts(agent: Any) -> None:
    @agent.tool
    async def sec_edgar_company_facts(
        context: RunContext,
        ticker: str,
        fact_tags: list[str] | None = None,
        limit_per_fact: int = 4,
    ) -> dict[str, Any]:
        del context
        return company_facts_impl(
            ticker,
            fact_tags=fact_tags,
            limit_per_fact=limit_per_fact,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _TOOL_NAMES[0], "register_func": register_company_profile},
        {"name": _TOOL_NAMES[1], "register_func": register_recent_filings},
        {"name": _TOOL_NAMES[2], "register_func": register_company_facts},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return list(_TOOL_NAMES)


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
