from __future__ import annotations

import json
import re
import time
from typing import Any

from ..android_input_kit.tooling import android_input_swipe, android_input_tap
from ..android_screen_capture_kit.tooling import android_capture_screenshot

DEFAULT_SETTLE_MS = 250
MAX_PAGE_TURNS = 50
MAX_SCROLL_PASSES = 10
MAX_ITEM_TAPS = 20


class CrawlPlanError(ValueError):
    pass


SwipeSpec = dict[str, int]
TapSpec = dict[str, int]
PageTurn = dict[str, Any]
ItemTap = dict[str, Any]


def _require_dict(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CrawlPlanError(f"{label} must be a JSON object")
    return value


def _require_int(value: Any, *, label: str, minimum: int | None = None) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise CrawlPlanError(f"{label} must be an integer") from exc
    if minimum is not None and number < minimum:
        raise CrawlPlanError(f"{label} must be >= {minimum}")
    return number


def _optional_str(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _slugify(value: str, *, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    slug = slug.strip("-")
    return slug or fallback


def _parse_tap(raw: Any, *, label: str) -> TapSpec:
    payload = _require_dict(raw, label=label)
    return {
        "x": _require_int(payload.get("x"), label=f"{label}.x", minimum=0),
        "y": _require_int(payload.get("y"), label=f"{label}.y", minimum=0),
    }


def _parse_swipe(raw: Any, *, label: str) -> SwipeSpec:
    payload = _require_dict(raw, label=label)
    return {
        "x1": _require_int(payload.get("x1"), label=f"{label}.x1", minimum=0),
        "y1": _require_int(payload.get("y1"), label=f"{label}.y1", minimum=0),
        "x2": _require_int(payload.get("x2"), label=f"{label}.x2", minimum=0),
        "y2": _require_int(payload.get("y2"), label=f"{label}.y2", minimum=0),
        "duration_ms": _require_int(
            payload.get("duration_ms", 300),
            label=f"{label}.duration_ms",
            minimum=1,
        ),
    }


def _parse_page_turns(raw: Any) -> list[PageTurn]:
    if raw in (None, []):
        return []
    if not isinstance(raw, list):
        raise CrawlPlanError("page_turns must be a JSON array")
    if len(raw) > MAX_PAGE_TURNS:
        raise CrawlPlanError(f"page_turns cannot exceed {MAX_PAGE_TURNS} entries")

    turns: list[PageTurn] = []
    for index, item in enumerate(raw, start=1):
        payload = _require_dict(item, label=f"page_turns[{index - 1}]")
        label = _optional_str(payload.get("label"), default=f"page-{index}")
        turns.append(
            {
                "label": label,
                "x": _require_int(
                    payload.get("x"), label=f"page_turns[{index - 1}].x", minimum=0
                ),
                "y": _require_int(
                    payload.get("y"), label=f"page_turns[{index - 1}].y", minimum=0
                ),
            }
        )
    return turns


def _parse_item_taps(raw: Any) -> list[ItemTap]:
    if raw in (None, []):
        return []
    if not isinstance(raw, list):
        raise CrawlPlanError("item_taps must be a JSON array")
    if len(raw) > MAX_ITEM_TAPS:
        raise CrawlPlanError(f"item_taps cannot exceed {MAX_ITEM_TAPS} entries")

    item_taps: list[ItemTap] = []
    for index, item in enumerate(raw, start=1):
        payload = _require_dict(item, label=f"item_taps[{index - 1}]")
        item_label = _optional_str(payload.get("label"), default=f"item-{index}")
        capture_stage = _slugify(
            _optional_str(payload.get("capture_stage"), default=f"detail-{item_label}"),
            fallback=f"detail-{index}",
        )
        close_tap = None
        if payload.get("close_tap") is not None:
            close_tap = _parse_tap(
                payload.get("close_tap"),
                label=f"item_taps[{index - 1}].close_tap",
            )
        item_taps.append(
            {
                "page_label": _optional_str(
                    payload.get("page_label"),
                    default="current",
                ),
                "label": item_label,
                "capture_stage": capture_stage,
                "x": _require_int(
                    payload.get("x"), label=f"item_taps[{index - 1}].x", minimum=0
                ),
                "y": _require_int(
                    payload.get("y"), label=f"item_taps[{index - 1}].y", minimum=0
                ),
                "close_tap": close_tap,
            }
        )
    return item_taps


def _parse_plan(plan_json: str) -> dict[str, Any]:
    text = str(plan_json or "").strip()
    if not text:
        raise CrawlPlanError("plan_json is required")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CrawlPlanError(f"plan_json must be valid JSON: {exc}") from exc

    payload = _require_dict(raw, label="plan")
    artifact_prefix = _slugify(
        _optional_str(
            payload.get("artifact_prefix"), default="android-paginated-crawl"
        ),
        fallback="android-paginated-crawl",
    )
    current_page_label = _optional_str(
        payload.get("current_page_label"), default="current"
    )
    capture_current_page = bool(payload.get("capture_current_page", True))
    scroll_passes_per_page = _require_int(
        payload.get("scroll_passes_per_page", 0),
        label="scroll_passes_per_page",
        minimum=0,
    )
    if scroll_passes_per_page > MAX_SCROLL_PASSES:
        raise CrawlPlanError(
            f"scroll_passes_per_page cannot exceed {MAX_SCROLL_PASSES}"
        )
    settle_ms = _require_int(
        payload.get("settle_ms", DEFAULT_SETTLE_MS),
        label="settle_ms",
        minimum=0,
    )
    page_turns = _parse_page_turns(payload.get("page_turns", []))
    item_taps = _parse_item_taps(payload.get("item_taps", []))
    if not capture_current_page and not page_turns:
        raise CrawlPlanError(
            "plan must capture the current page or include at least one page_turn"
        )

    capture_swipe = None
    if scroll_passes_per_page:
        capture_swipe = _parse_swipe(
            payload.get("capture_swipe"), label="capture_swipe"
        )

    pagination_recovery_swipe = None
    if payload.get("pagination_recovery_swipe") is not None:
        pagination_recovery_swipe = _parse_swipe(
            payload.get("pagination_recovery_swipe"),
            label="pagination_recovery_swipe",
        )

    return {
        "artifact_prefix": artifact_prefix,
        "current_page_label": current_page_label,
        "capture_current_page": capture_current_page,
        "page_turns": page_turns,
        "item_taps": item_taps,
        "scroll_passes_per_page": scroll_passes_per_page,
        "capture_swipe": capture_swipe,
        "pagination_recovery_swipe": pagination_recovery_swipe,
        "capture_after_recovery": bool(payload.get("capture_after_recovery", False)),
        "settle_ms": settle_ms,
    }


def _sleep_ms(settle_ms: int, *, dry_run: bool) -> None:
    if dry_run or settle_ms <= 0:
        return
    time.sleep(settle_ms / 1000)


def _capture_artifact_name(
    artifact_prefix: str,
    page_label: str,
    stage: str,
    *,
    pass_index: int | None = None,
) -> str:
    page_slug = _slugify(page_label, fallback="page")
    base = f"{artifact_prefix}_{page_slug}_{stage}"
    if pass_index is None:
        return base
    return f"{base}_{pass_index:02d}"


def _capture(
    artifact_prefix: str,
    page_label: str,
    stage: str,
    *,
    pass_index: int | None,
    dry_run: bool,
) -> dict[str, Any]:
    artifact_name = _capture_artifact_name(
        artifact_prefix,
        page_label,
        stage,
        pass_index=pass_index,
    )
    result = android_capture_screenshot(artifact_name=artifact_name, dry_run=dry_run)
    return {
        "artifact_name": artifact_name,
        "page_label": page_label,
        "stage": stage,
        "pass_index": pass_index,
        "result": result,
    }


def _item_taps_for_page(item_taps: list[ItemTap], page_label: str) -> list[ItemTap]:
    return [item for item in item_taps if item["page_label"] == page_label]


def _run_item_taps(
    *,
    item_taps: list[ItemTap],
    artifact_prefix: str,
    page_label: str,
    dry_run: bool,
    settle_ms: int,
    actions: list[dict[str, Any]],
    captures: list[dict[str, Any]],
) -> None:
    for item in item_taps:
        tap_result = android_input_tap(x=item["x"], y=item["y"], dry_run=dry_run)
        actions.append(
            {
                "kind": "item_tap",
                "page_label": page_label,
                "label": item["label"],
                "x": item["x"],
                "y": item["y"],
                "result": tap_result,
            }
        )
        _sleep_ms(settle_ms, dry_run=dry_run)
        captures.append(
            _capture(
                artifact_prefix,
                page_label,
                item["capture_stage"],
                pass_index=None,
                dry_run=dry_run,
            )
        )

        if item["close_tap"] is not None:
            close_tap = item["close_tap"]
            close_result = android_input_tap(
                x=close_tap["x"],
                y=close_tap["y"],
                dry_run=dry_run,
            )
            actions.append(
                {
                    "kind": "detail_close_tap",
                    "page_label": page_label,
                    "label": item["label"],
                    "x": close_tap["x"],
                    "y": close_tap["y"],
                    "result": close_result,
                }
            )
            _sleep_ms(settle_ms, dry_run=dry_run)


def android_paginated_crawl_doctor() -> dict[str, Any]:
    return {
        "success": True,
        "summary": (
            "Plan-driven Android crawl helper for paginated mobile lists. "
            "It handles pagination recovery swipes, page taps, optional item/detail taps, "
            "content scrolls, and screenshot capture loops."
        ),
        "required_plan_fields": [
            "artifact_prefix",
            "capture_current_page or page_turns",
        ],
        "optional_plan_fields": [
            "current_page_label",
            "page_turns",
            "item_taps",
            "pagination_recovery_swipe",
            "scroll_passes_per_page",
            "capture_swipe",
            "capture_after_recovery",
            "settle_ms",
        ],
        "guidance": [
            "Use pagination_recovery_swipe when page buttons live near the bottom and footer fluff causes overshoot.",
            "Use item_taps when one visible row should be opened and captured before the next scroll pass.",
            "Keep the plan tiny and deterministic; don’t turn it into a Turing-complete swamp monster.",
        ],
    }


def android_paginated_crawl_examples() -> dict[str, Any]:
    example_plan = {
        "artifact_prefix": "freecash-sample",
        "current_page_label": "3",
        "capture_current_page": True,
        "pagination_recovery_swipe": {
            "x1": 550,
            "y1": 1460,
            "x2": 550,
            "y2": 1750,
            "duration_ms": 250,
        },
        "page_turns": [
            {"label": "4", "x": 994, "y": 1908},
            {"label": "27", "x": 861, "y": 1908},
        ],
        "item_taps": [
            {
                "page_label": "3",
                "label": "screw-guru",
                "x": 472,
                "y": 1492,
                "capture_stage": "detail-screw-guru",
                "close_tap": {"x": 1008, "y": 1185},
            }
        ],
        "scroll_passes_per_page": 2,
        "capture_swipe": {
            "x1": 550,
            "y1": 1830,
            "x2": 550,
            "y2": 1410,
            "duration_ms": 350,
        },
        "capture_after_recovery": False,
        "settle_ms": 250,
    }
    return {
        "success": True,
        "example_plan_json": json.dumps(example_plan, indent=2),
        "notes": [
            "This is designed for lists where pagination buttons are visible but finicky.",
            "Item taps let you open one visible row, capture the modal, close it, then continue the crawl.",
        ],
    }


def android_paginated_crawl_run(
    plan_json: str,
    dry_run: bool = True,
) -> dict[str, Any]:
    plan = _parse_plan(plan_json)
    actions: list[dict[str, Any]] = []
    captures: list[dict[str, Any]] = []

    def record_capture(
        page_label: str, stage: str, pass_index: int | None = None
    ) -> None:
        captures.append(
            _capture(
                plan["artifact_prefix"],
                page_label,
                stage,
                pass_index=pass_index,
                dry_run=dry_run,
            )
        )

    current_page_label = plan["current_page_label"]
    if plan["capture_current_page"]:
        record_capture(current_page_label, "top")
    _run_item_taps(
        item_taps=_item_taps_for_page(plan["item_taps"], current_page_label),
        artifact_prefix=plan["artifact_prefix"],
        page_label=current_page_label,
        dry_run=dry_run,
        settle_ms=plan["settle_ms"],
        actions=actions,
        captures=captures,
    )

    for turn in plan["page_turns"]:
        recovery = plan["pagination_recovery_swipe"]
        if recovery is not None:
            recovery_result = android_input_swipe(dry_run=dry_run, **recovery)
            actions.append(
                {
                    "kind": "pagination_recovery_swipe",
                    "page_label": turn["label"],
                    "result": recovery_result,
                }
            )
            _sleep_ms(plan["settle_ms"], dry_run=dry_run)
            if plan["capture_after_recovery"]:
                record_capture(turn["label"], "recovered")

        tap_result = android_input_tap(x=turn["x"], y=turn["y"], dry_run=dry_run)
        actions.append(
            {
                "kind": "page_tap",
                "page_label": turn["label"],
                "x": turn["x"],
                "y": turn["y"],
                "result": tap_result,
            }
        )
        _sleep_ms(plan["settle_ms"], dry_run=dry_run)
        record_capture(turn["label"], "top")
        _run_item_taps(
            item_taps=_item_taps_for_page(plan["item_taps"], turn["label"]),
            artifact_prefix=plan["artifact_prefix"],
            page_label=turn["label"],
            dry_run=dry_run,
            settle_ms=plan["settle_ms"],
            actions=actions,
            captures=captures,
        )

        for pass_index in range(1, plan["scroll_passes_per_page"] + 1):
            swipe_result = android_input_swipe(
                dry_run=dry_run,
                **plan["capture_swipe"],
            )
            actions.append(
                {
                    "kind": "content_swipe",
                    "page_label": turn["label"],
                    "pass_index": pass_index,
                    "result": swipe_result,
                }
            )
            _sleep_ms(plan["settle_ms"], dry_run=dry_run)
            record_capture(turn["label"], "scroll", pass_index=pass_index)

    return {
        "success": True,
        "dry_run": dry_run,
        "plan": plan,
        "actions": actions,
        "captures": captures,
        "capture_count": len(captures),
        "action_count": len(actions),
    }
