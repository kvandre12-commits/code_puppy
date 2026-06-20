from __future__ import annotations

from pathlib import Path
from typing import Any

from .lease_store import LeaseRecord


def _normalize_constraint_values(values: Any, *, lower: bool = False) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        if lower:
            text = text.lower()
        if text not in cleaned:
            cleaned.append(text)
    return cleaned


def _path_matches_any(candidate: str, allowed_paths: list[str]) -> bool:
    if not candidate:
        return False
    candidate_path = Path(candidate).expanduser().resolve()
    for allowed in allowed_paths:
        try:
            candidate_path.relative_to(Path(allowed).expanduser().resolve())
            return True
        except ValueError:
            continue
    return False


def _looks_like_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def lease_constraint_failure(
    record: LeaseRecord,
    *,
    tool_name: str,
    tool_args: dict[str, Any],
) -> str | None:
    constraints = record.constraints
    allowed_paths = _normalize_constraint_values(constraints.get("allowed_paths"))
    intent_actions = _normalize_constraint_values(constraints.get("intent_actions"))
    intent_packages = _normalize_constraint_values(
        constraints.get("intent_packages"), lower=True
    )
    browser_packages = _normalize_constraint_values(
        constraints.get("browser_packages"), lower=True
    )

    if tool_name == "android_intent_send":
        action = str(tool_args.get("action", "")).strip()
        package_name = str(tool_args.get("package_name", "")).strip().lower()
        if intent_actions and action not in intent_actions:
            return "[BLOCKED] Lease only allows specific Android intent actions."
        if intent_packages:
            if not package_name:
                return "[BLOCKED] Lease requires an explicit Android package target."
            if package_name not in intent_packages:
                return "[BLOCKED] Lease only allows specific Android intent packages."

    if tool_name == "android_handoff_file" and allowed_paths:
        file_path = str(tool_args.get("file_path", "")).strip()
        if not _path_matches_any(file_path, allowed_paths):
            return "[BLOCKED] Lease only allows file actions within approved paths."

    if tool_name == "agent_run_shell_command" and allowed_paths:
        cwd = str(tool_args.get("cwd", "")).strip()
        if not cwd:
            return (
                "[BLOCKED] Path-locked shell leases require an explicit cwd inside an "
                "approved path."
            )
        if not _path_matches_any(cwd, allowed_paths):
            return "[BLOCKED] Lease only allows shell execution within approved paths."

    if browser_packages:
        browser_locked_call = tool_name == "android_browser_open_url" or (
            tool_name == "android_open"
            and _looks_like_url(str(tool_args.get("target", "")).strip())
        )
        if browser_locked_call:
            browser = str(tool_args.get("browser", "brave")).strip().lower()
            if browser not in browser_packages:
                return "[BLOCKED] Lease only allows specific browser packages."

    return None
