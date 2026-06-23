"""Deterministic proof harness for doctrine-guided mutation changes."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .doctrine_consultation import DoctrineMutationCheck, analyze_mutation


@dataclass(slots=True, frozen=True)
class MutationProofResult:
    """Outcome of simulating a doctrine challenge against a mutation plan."""

    warning_message: str
    original_tool_name: str
    original_tool_args: dict[str, Any]
    adapted_tool_name: str
    adapted_tool_args: dict[str, Any]
    original_plan: str
    adapted_plan: str
    doctrine_decision_ids: tuple[str, ...]
    changed_plan: bool
    patch_differs: bool


def prove_doctrine_guided_mutation(
    tool_name: str,
    tool_args: dict[str, Any] | None,
) -> MutationProofResult | None:
    """Simulate how doctrine would change a proposed dependency mutation."""
    check = analyze_mutation(tool_name, tool_args)
    if check is None:
        return None

    original_args = deepcopy(tool_args or {})
    adapted_args = _adapt_tool_args(
        tool_name=tool_name, tool_args=original_args, check=check
    )
    decision_ids = tuple(conflict.decision.id for conflict in check.conflicts)

    return MutationProofResult(
        warning_message=check.warning_message,
        original_tool_name=tool_name,
        original_tool_args=original_args,
        adapted_tool_name=tool_name,
        adapted_tool_args=adapted_args,
        original_plan=_describe_original_plan(tool_name, check),
        adapted_plan=_describe_adapted_plan(tool_name, check, adapted_args),
        doctrine_decision_ids=decision_ids,
        changed_plan=adapted_args != original_args,
        patch_differs=adapted_args != original_args,
    )


def _describe_original_plan(tool_name: str, check: DoctrineMutationCheck) -> str:
    packages = ", ".join(check.added_packages)
    return f"{tool_name} would add dependency signal [{packages}] in {check.file_path}."


def _describe_adapted_plan(
    tool_name: str,
    check: DoctrineMutationCheck,
    adapted_args: dict[str, Any],
) -> str:
    del adapted_args
    packages = ", ".join(check.conflicting_packages)
    decision_ids = ", ".join(conflict.decision.id for conflict in check.conflicts)
    return (
        f"{tool_name} is revised to avoid adding [{packages}] after doctrine "
        f"challenge from [{decision_ids}]."
    )


def _adapt_tool_args(
    *,
    tool_name: str,
    tool_args: dict[str, Any],
    check: DoctrineMutationCheck,
) -> dict[str, Any]:
    adapted = deepcopy(tool_args)
    blocked_packages = set(check.conflicting_packages)

    if tool_name == "create_file":
        adapted["content"] = _strip_conflicting_lines(
            str(adapted.get("content", "") or ""),
            blocked_packages,
        )
        return adapted

    if tool_name != "replace_in_file":
        return adapted

    replacements = []
    for replacement in adapted.get("replacements") or []:
        if not isinstance(replacement, dict):
            replacements.append(replacement)
            continue
        next_replacement = dict(replacement)
        next_replacement["new_str"] = _strip_conflicting_lines(
            str(next_replacement.get("new_str", "") or ""),
            blocked_packages,
        )
        replacements.append(next_replacement)
    adapted["replacements"] = replacements
    return adapted


def _strip_conflicting_lines(content: str, blocked_packages: set[str]) -> str:
    if not blocked_packages:
        return content

    kept_lines: list[str] = []
    for line in content.splitlines(keepends=True):
        lowered = line.lower()
        if any(package in lowered for package in blocked_packages):
            continue
        kept_lines.append(line)
    return "".join(kept_lines)
