"""Register Shopify store launch kit tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .brand_model import (
    shopify_brand_product_model_create as shopify_brand_product_model_create_impl,
)
from .product_story import (
    shopify_collective_search_batch_create as shopify_collective_search_batch_create_impl,
    shopify_first_ten_story_create as shopify_first_ten_story_create_impl,
    shopify_product_hunt_run as shopify_product_hunt_run_impl,
    shopify_product_story_fit_report as shopify_product_story_fit_report_impl,
)
from .winner_board import shopify_winner_board_build as shopify_winner_board_build_impl
from .tooling import (
    shopify_admin_navigation_helper as shopify_admin_navigation_helper_impl,
    shopify_import_prompt_create as shopify_import_prompt_create_impl,
    shopify_product_curation_capture as shopify_product_curation_capture_impl,
    shopify_store_launch_kit_doctor as shopify_store_launch_kit_doctor_impl,
    shopify_store_launch_plan_create as shopify_store_launch_plan_create_impl,
    shopify_store_launch_template as shopify_store_launch_template_impl,
)

_DOCTOR = "shopify_store_launch_kit_doctor"
_TEMPLATE = "shopify_store_launch_template"
_PLAN_CREATE = "shopify_store_launch_plan_create"
_CURATION_CAPTURE = "shopify_product_curation_capture"
_IMPORT_PROMPT = "shopify_import_prompt_create"
_NAV_HELPER = "shopify_admin_navigation_helper"
_BRAND_MODEL = "shopify_brand_product_model_create"
_FIRST_TEN_STORY = "shopify_first_ten_story_create"
_STORY_FIT = "shopify_product_story_fit_report"
_SEARCH_BATCH = "shopify_collective_search_batch_create"
_HUNT_RUN = "shopify_product_hunt_run"
_WINNER_BOARD = "shopify_winner_board_build"


def register_shopify_store_launch_kit_doctor(agent: Any) -> None:
    @agent.tool
    async def shopify_store_launch_kit_doctor(context: RunContext) -> dict[str, Any]:
        del context
        return shopify_store_launch_kit_doctor_impl()


def register_shopify_store_launch_template(agent: Any) -> None:
    @agent.tool
    async def shopify_store_launch_template(
        context: RunContext,
        lane: str = "desk_operator",
    ) -> dict[str, Any]:
        del context
        return shopify_store_launch_template_impl(lane=lane)


def register_shopify_store_launch_plan_create(agent: Any) -> None:
    @agent.tool
    async def shopify_store_launch_plan_create(
        context: RunContext,
        store_name: str,
        primary_lane: str = "desk_operator",
        secondary_lane: str = "kitchen_prep",
        starter_goal: str = "Stock 5-10 real Shopify Collective products and prepare launch pages.",
        artifact_name: str = "shopify_store_launch_plan",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return shopify_store_launch_plan_create_impl(
            store_name=store_name,
            primary_lane=primary_lane,
            secondary_lane=secondary_lane,
            starter_goal=starter_goal,
            artifact_name=artifact_name,
            dry_run=dry_run,
        )


def register_shopify_product_curation_capture(agent: Any) -> None:
    @agent.tool
    async def shopify_product_curation_capture(
        context: RunContext,
        store_name: str,
        lane: str = "desk_operator",
        candidates: list[dict[str, Any]] | None = None,
        priority_terms: list[str] | None = None,
        artifact_name: str = "shopify_product_curation",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return shopify_product_curation_capture_impl(
            store_name=store_name,
            lane=lane,
            candidates=candidates,
            priority_terms=priority_terms,
            artifact_name=artifact_name,
            dry_run=dry_run,
        )


def register_shopify_import_prompt_create(agent: Any) -> None:
    @agent.tool
    async def shopify_import_prompt_create(
        context: RunContext,
        candidate: dict[str, Any],
        artifact_name: str = "shopify_import_prompt",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return shopify_import_prompt_create_impl(
            candidate=candidate,
            artifact_name=artifact_name,
            dry_run=dry_run,
        )


def register_shopify_admin_navigation_helper(agent: Any) -> None:
    @agent.tool
    async def shopify_admin_navigation_helper(
        context: RunContext,
        store_slug: str,
        target: str = "collective_discovery",
    ) -> dict[str, Any]:
        del context
        return shopify_admin_navigation_helper_impl(
            store_slug=store_slug,
            target=target,
        )


def register_shopify_brand_product_model_create(agent: Any) -> None:
    @agent.tool
    async def shopify_brand_product_model_create(
        context: RunContext,
        store_name: str,
        model_name: str = "operator_station",
        extra_search_terms: list[str] | None = None,
        artifact_name: str = "shopify_brand_product_model",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return shopify_brand_product_model_create_impl(
            store_name=store_name,
            model_name=model_name,
            extra_search_terms=extra_search_terms,
            artifact_name=artifact_name,
            dry_run=dry_run,
        )


def register_shopify_first_ten_story_create(agent: Any) -> None:
    @agent.tool
    async def shopify_first_ten_story_create(
        context: RunContext,
        store_name: str,
        model_name: str = "operator_station",
        artifact_name: str = "shopify_first_ten_story",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return shopify_first_ten_story_create_impl(
            store_name=store_name,
            model_name=model_name,
            artifact_name=artifact_name,
            dry_run=dry_run,
        )


def register_shopify_product_story_fit_report(agent: Any) -> None:
    @agent.tool
    async def shopify_product_story_fit_report(
        context: RunContext,
        store_name: str,
        candidates: list[dict[str, Any]],
        model_name: str = "operator_station",
        artifact_name: str = "shopify_product_story_fit",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return shopify_product_story_fit_report_impl(
            store_name=store_name,
            candidates=candidates,
            model_name=model_name,
            artifact_name=artifact_name,
            dry_run=dry_run,
        )


def register_shopify_product_hunt_run(agent: Any) -> None:
    @agent.tool
    async def shopify_product_hunt_run(
        context: RunContext,
        store_name: str,
        store_slug: str,
        candidates: list[dict[str, Any]] | None = None,
        model_name: str = "operator_station",
        artifact_name: str = "shopify_product_hunt_run",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return shopify_product_hunt_run_impl(
            store_name=store_name,
            store_slug=store_slug,
            candidates=candidates,
            model_name=model_name,
            artifact_name=artifact_name,
            dry_run=dry_run,
        )


def register_shopify_collective_search_batch_create(agent: Any) -> None:
    @agent.tool
    async def shopify_collective_search_batch_create(
        context: RunContext,
        store_slug: str,
        model_name: str = "operator_station",
    ) -> dict[str, Any]:
        del context
        return shopify_collective_search_batch_create_impl(
            store_slug=store_slug,
            model_name=model_name,
        )


def register_shopify_winner_board_build(agent: Any) -> None:
    @agent.tool
    async def shopify_winner_board_build(
        context: RunContext,
        store_name: str,
        candidates: list[dict[str, Any]],
        model_name: str = "operator_station",
        artifact_name: str = "shopify_winner_board",
        dry_run: bool = True,
    ) -> dict[str, Any]:
        del context
        return shopify_winner_board_build_impl(
            store_name=store_name,
            candidates=candidates,
            model_name=model_name,
            artifact_name=artifact_name,
            dry_run=dry_run,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR, "register_func": register_shopify_store_launch_kit_doctor},
        {"name": _TEMPLATE, "register_func": register_shopify_store_launch_template},
        {
            "name": _PLAN_CREATE,
            "register_func": register_shopify_store_launch_plan_create,
        },
        {
            "name": _CURATION_CAPTURE,
            "register_func": register_shopify_product_curation_capture,
        },
        {
            "name": _IMPORT_PROMPT,
            "register_func": register_shopify_import_prompt_create,
        },
        {
            "name": _NAV_HELPER,
            "register_func": register_shopify_admin_navigation_helper,
        },
        {
            "name": _BRAND_MODEL,
            "register_func": register_shopify_brand_product_model_create,
        },
        {
            "name": _FIRST_TEN_STORY,
            "register_func": register_shopify_first_ten_story_create,
        },
        {
            "name": _STORY_FIT,
            "register_func": register_shopify_product_story_fit_report,
        },
        {
            "name": _SEARCH_BATCH,
            "register_func": register_shopify_collective_search_batch_create,
        },
        {
            "name": _HUNT_RUN,
            "register_func": register_shopify_product_hunt_run,
        },
        {
            "name": _WINNER_BOARD,
            "register_func": register_shopify_winner_board_build,
        },
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [
        _DOCTOR,
        _TEMPLATE,
        _PLAN_CREATE,
        _CURATION_CAPTURE,
        _IMPORT_PROMPT,
        _NAV_HELPER,
        _BRAND_MODEL,
        _FIRST_TEN_STORY,
        _STORY_FIT,
        _SEARCH_BATCH,
        _HUNT_RUN,
        _WINNER_BOARD,
    ]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
