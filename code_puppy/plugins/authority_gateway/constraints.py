from __future__ import annotations

import re
import shutil
import subprocess
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


def _foreground_android_package() -> str:
    adb = shutil.which("adb")
    if not adb:
        return ""
    commands = [
        [adb, "shell", "dumpsys", "window", "windows"],
        [adb, "shell", "dumpsys", "activity", "activities"],
    ]
    patterns = (
        re.compile(r"mCurrentFocus=.*?\s([A-Za-z0-9_.]+)/[A-Za-z0-9_.$]+"),
        re.compile(r"topResumedActivity:.*?\s([A-Za-z0-9_.]+)/[A-Za-z0-9_.$]+"),
        re.compile(r"mFocusedApp=.*?\s([A-Za-z0-9_.]+)/[A-Za-z0-9_.$]+"),
    )
    for command in commands:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        haystack = "\n".join([completed.stdout or "", completed.stderr or ""])
        for pattern in patterns:
            match = pattern.search(haystack)
            if match:
                return match.group(1).strip().lower()
    return ""


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
    android_packages = _normalize_constraint_values(
        constraints.get("android_packages"), lower=True
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

    if android_packages:
        package_arg = str(tool_args.get("package_name", "")).strip().lower()
        if tool_name in {"android_launch_app", "android_intent_send"}:
            if not package_arg:
                return "[BLOCKED] Lease requires an explicit Android package target."
            if package_arg not in android_packages:
                return "[BLOCKED] Lease only allows specific Android packages."
        if tool_name in {
            "android_input_keyevent",
            "android_input_swipe",
            "android_input_tap",
            "android_input_tap_bounds",
            "android_input_text",
            "android_ui_tap_match",
            "android_ui_text_into_match",
        }:
            foreground_package = _foreground_android_package()
            if not foreground_package:
                return "[BLOCKED] Could not verify the foreground Android package for this lease."
            if foreground_package not in android_packages:
                return "[BLOCKED] Lease only allows Android input while specific packages are foregrounded."

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
