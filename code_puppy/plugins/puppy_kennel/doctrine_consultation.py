"""Mutation-time doctrine consultation for puppy_kennel.

This is intentionally narrow:
- one interception seam: ``pre_tool_call``
- one mutation family: dependency-file edits
- one behavior: warning-only doctrine challenge

No ontology growth. No hard blocks. Just a well-timed throat-clear.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from code_puppy.messaging import emit_warning

from .decisions import DecisionRecord, get_active_decisions_for_cwd
from .state import is_enabled

_MUTATION_TOOLS = frozenset({"create_file", "replace_in_file"})
_DEPENDENCY_FILE_NAMES = frozenset(
    {
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "requirements.in",
        "requirements-dev.in",
    }
)
_REQUIREMENTS_PREFIXES = ("requirements-",)
_REQ_NAME_RE = re.compile(
    r"^\s*['\"]?([A-Za-z0-9][A-Za-z0-9_.-]*)(?:\[[^\]]+\])?\s*(?:[<>=!~].*)?$"
)


def build_pre_tool_response(
    tool_name: str,
    tool_args: dict[str, Any] | None,
) -> dict[str, str] | None:
    """Return a warning-only hook payload when doctrine challenges a mutation."""
    if not is_enabled() or tool_name not in _MUTATION_TOOLS:
        return None

    args = tool_args or {}
    file_path = _extract_file_path(args)
    if not file_path or not _is_dependency_file(file_path):
        return None

    added_packages = _infer_added_packages(tool_name=tool_name, tool_args=args)
    if not added_packages:
        return None

    decisions = get_active_decisions_for_cwd(Path.cwd())
    conflicts = _find_conflicts(added_packages=added_packages, decisions=decisions)
    if not conflicts:
        return None

    message = _render_warning(
        file_path=file_path,
        added_packages=added_packages,
        conflicts=conflicts,
    )
    emit_warning(message)
    return {"context_message": message}


def _extract_file_path(tool_args: dict[str, Any]) -> str:
    return str(tool_args.get("file_path", "") or "").strip()


def _is_dependency_file(file_path: str) -> bool:
    name = Path(file_path).name.lower()
    return name in _DEPENDENCY_FILE_NAMES or any(
        name.startswith(prefix) for prefix in _REQUIREMENTS_PREFIXES
    )


def _infer_added_packages(tool_name: str, tool_args: dict[str, Any]) -> list[str]:
    if tool_name == "create_file":
        return sorted(
            _packages_from_content(
                Path(_extract_file_path(tool_args)).name,
                str(tool_args.get("content", "") or ""),
            )
        )

    if tool_name != "replace_in_file":
        return []

    added: set[str] = set()
    for replacement in tool_args.get("replacements") or []:
        if not isinstance(replacement, dict):
            continue
        old_packages = _packages_from_content(
            Path(_extract_file_path(tool_args)).name,
            str(replacement.get("old_str", "") or ""),
        )
        new_packages = _packages_from_content(
            Path(_extract_file_path(tool_args)).name,
            str(replacement.get("new_str", "") or ""),
        )
        added.update(new_packages - old_packages)
    return sorted(added)


def _packages_from_content(file_name: str, content: str) -> set[str]:
    lowered_name = (file_name or "").lower()
    if lowered_name == "pyproject.toml":
        return _packages_from_pyproject_like_text(content)
    if lowered_name.startswith("requirements"):
        return _packages_from_requirements_text(content)
    return set()


def _packages_from_pyproject_like_text(content: str) -> set[str]:
    packages: set[str] = set()
    for raw_line in (content or "").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if "=" in line and not any(ch in line for ch in ('"', "'")):
            continue
        candidate = line.rstrip(",").strip().strip('"').strip("'")
        name = _extract_requirement_name(candidate)
        if name:
            packages.add(name)
    return packages


def _packages_from_requirements_text(content: str) -> set[str]:
    packages: set[str] = set()
    for raw_line in (content or "").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith(("-", ".", "http://", "https://")):
            continue
        name = _extract_requirement_name(line)
        if name:
            packages.add(name)
    return packages


def _extract_requirement_name(spec: str) -> str | None:
    candidate = str(spec or "").strip()
    if not candidate:
        return None
    candidate = candidate.split(";", 1)[0].strip()
    match = _REQ_NAME_RE.match(candidate)
    if not match:
        return None
    normalized = match.group(1).strip().lower()
    return normalized or None


def _find_conflicts(
    *,
    added_packages: list[str],
    decisions: list[DecisionRecord],
) -> list[tuple[str, DecisionRecord]]:
    conflicts: list[tuple[str, DecisionRecord]] = []
    seen: set[tuple[str, str]] = set()
    for package_name in added_packages:
        needle = re.compile(
            rf"(?<![a-z0-9]){re.escape(package_name.lower())}(?![a-z0-9])"
        )
        for decision in decisions:
            haystack = " ".join(
                [
                    decision.id,
                    decision.title,
                    decision.summary,
                    decision.rationale,
                    " ".join(decision.evidence_artifact_ids),
                ]
            ).lower()
            if not needle.search(haystack):
                continue
            key = (package_name, decision.id)
            if key in seen:
                continue
            seen.add(key)
            conflicts.append((package_name, decision))
    return conflicts


def _render_warning(
    *,
    file_path: str,
    added_packages: list[str],
    conflicts: list[tuple[str, DecisionRecord]],
) -> str:
    lines = [
        "[doctrine check] Potential conflict detected before dependency-file edit.",
        f"Target: {file_path}",
        f"Proposed dependency signal: {', '.join(added_packages)}",
        "This is a warning only. The tool call will continue.",
    ]
    for package_name, decision in conflicts:
        evidence = ", ".join(decision.evidence_artifact_ids) or "none recorded"
        lines.extend(
            [
                "",
                f"Package: {package_name}",
                f"Decision: {decision.title}",
                f"Decision ID: {decision.id}",
                f"Status: {decision.status}",
                f"Confidence: {decision.confidence}",
                f"Rationale: {decision.rationale}",
                f"Evidence: {evidence}",
                (
                    "Drill-down: /kennel doctrine "
                    f'{decision.id} or kennel_get_decision(decision_id="{decision.id}")'
                ),
            ]
        )
    return "\n".join(lines)
