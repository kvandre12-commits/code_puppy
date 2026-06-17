from __future__ import annotations

from typing import Any

from ..android_input_kit.tooling import (
    android_input_keyevent,
    android_input_tap_bounds,
    android_input_text,
)
from ..android_ui_dump_kit.tooling import android_ui_dump_find


def android_ui_action_doctor() -> dict[str, Any]:
    return {
        "success": True,
        "guidance": [
            "Use dry_run first to inspect the matched node and generated actions.",
            "Combine query/resource_id/class_name filters to narrow the target.",
            "Keep the phone awake and unlocked during UI actions.",
        ],
        "example_flows": [
            "find node by text -> tap bounds",
            "find input field -> tap -> type text",
            "find button -> tap matched node",
        ],
    }



def _pick_match(
    query: str = "",
    resource_id: str = "",
    class_name: str = "",
    clickable_only: bool = False,
    match_index: int = 0,
) -> dict[str, Any]:
    result = android_ui_dump_find(
        query=query,
        resource_id=resource_id,
        class_name=class_name,
        clickable_only=clickable_only,
        max_results=max(50, match_index + 1),
    )
    matches = result.get("matches", [])
    if not matches:
        raise RuntimeError("No matching UI nodes found")
    if match_index < 0 or match_index >= len(matches):
        raise RuntimeError(
            f"match_index {match_index} is out of range for {len(matches)} matches"
        )
    return matches[match_index]



def android_ui_tap_match(
    query: str = "",
    resource_id: str = "",
    class_name: str = "",
    clickable_only: bool = True,
    match_index: int = 0,
    dry_run: bool = True,
) -> dict[str, Any]:
    match = _pick_match(
        query=query,
        resource_id=resource_id,
        class_name=class_name,
        clickable_only=clickable_only,
        match_index=match_index,
    )
    tap_result = android_input_tap_bounds(match["bounds"], dry_run=dry_run)
    return {
        "success": tap_result.get("success", False),
        "dry_run": dry_run,
        "match": match,
        "tap": tap_result,
    }



def android_ui_text_into_match(
    value: str,
    query: str = "",
    resource_id: str = "",
    class_name: str = "",
    clickable_only: bool = False,
    match_index: int = 0,
    dry_run: bool = True,
    submit: bool = False,
) -> dict[str, Any]:
    if not value:
        raise ValueError("value is required")
    match = _pick_match(
        query=query,
        resource_id=resource_id,
        class_name=class_name,
        clickable_only=clickable_only,
        match_index=match_index,
    )
    tap_result = android_input_tap_bounds(match["bounds"], dry_run=dry_run)
    text_result = android_input_text(value, dry_run=dry_run)
    submit_result = None
    if submit:
        submit_result = android_input_keyevent("KEYCODE_ENTER", dry_run=dry_run)
    return {
        "success": tap_result.get("success", False) and text_result.get("success", False),
        "dry_run": dry_run,
        "match": match,
        "tap": tap_result,
        "text": text_result,
        "submit": submit_result,
    }
