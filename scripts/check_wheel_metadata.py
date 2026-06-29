#!/usr/bin/env python3
"""Verify that built wheel metadata matches pyproject dependency intent."""

from __future__ import annotations

import argparse
import re
import tomllib
import zipfile
from collections import defaultdict
from pathlib import Path

REQUIRES_DIST_PREFIX = "Requires-Dist: "
EXTRA_PATTERN = re.compile(r"extra\s*==\s*['\"]([^'\"]+)['\"]")
NAME_PATTERN = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
FORBIDDEN_BASE_DEPENDENCIES = {
    "anthropic",
    "azure-identity",
    "boto3",
    "mcp",
    "openai",
    "pillow",
    "playwright",
    "rapidfuzz",
    "ripgrep",
    "tree-sitter-typescript",
}


def _normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement_name(requirement: str) -> str:
    match = NAME_PATTERN.match(requirement)
    if not match:
        raise ValueError(f"Could not parse requirement name from: {requirement!r}")
    return _normalize_name(match.group(1))


def _extract_metadata_lines(wheel_path: Path) -> list[str]:
    with zipfile.ZipFile(wheel_path) as zf:
        metadata_name = next(
            name for name in zf.namelist() if name.endswith(".dist-info/METADATA")
        )
        metadata = zf.read(metadata_name).decode()
    return metadata.splitlines()


def _parse_wheel_requirements(
    wheel_path: Path,
) -> tuple[set[str], dict[str, set[str]], list[str]]:
    base_requirements: set[str] = set()
    extra_requirements: dict[str, set[str]] = defaultdict(set)
    raw_requires_dist: list[str] = []

    for line in _extract_metadata_lines(wheel_path):
        if not line.startswith(REQUIRES_DIST_PREFIX):
            continue
        payload = line[len(REQUIRES_DIST_PREFIX) :]
        raw_requires_dist.append(payload)
        requirement, _, marker = payload.partition(";")
        requirement_name = _requirement_name(requirement)
        extra_match = EXTRA_PATTERN.search(marker)
        if extra_match:
            extra_requirements[extra_match.group(1)].add(requirement_name)
        else:
            base_requirements.add(requirement_name)

    return base_requirements, dict(extra_requirements), raw_requires_dist


def _load_pyproject_requirements(
    pyproject_path: Path,
) -> tuple[set[str], dict[str, set[str]]]:
    data = tomllib.loads(pyproject_path.read_text())
    project = data["project"]
    base_requirements = {
        _requirement_name(requirement)
        for requirement in project.get("dependencies", [])
    }
    extra_requirements = {
        extra_name: {_requirement_name(requirement) for requirement in requirements}
        for extra_name, requirements in project.get("optional-dependencies", {}).items()
    }
    return base_requirements, extra_requirements


def _render_dependency_block(title: str, values: set[str]) -> str:
    ordered = ", ".join(sorted(values)) if values else "<none>"
    return f"{title}: {ordered}"


def verify_wheel_metadata(wheel_path: Path, pyproject_path: Path) -> list[str]:
    expected_base, expected_extras = _load_pyproject_requirements(pyproject_path)
    actual_base, actual_extras, raw_requires_dist = _parse_wheel_requirements(
        wheel_path
    )
    errors: list[str] = []

    missing_base = expected_base - actual_base
    unexpected_base = actual_base - expected_base
    forbidden_base = actual_base & FORBIDDEN_BASE_DEPENDENCIES

    if missing_base:
        errors.append(
            _render_dependency_block("Missing base requirements", missing_base)
        )
    if unexpected_base:
        errors.append(
            _render_dependency_block("Unexpected base requirements", unexpected_base)
        )
    if forbidden_base:
        errors.append(
            _render_dependency_block(
                "Forbidden optional-heavy deps leaked into base", forbidden_base
            )
        )

    missing_extras = set(expected_extras) - set(actual_extras)
    unexpected_extras = set(actual_extras) - set(expected_extras)
    if missing_extras:
        errors.append(_render_dependency_block("Missing extras", missing_extras))
    if unexpected_extras:
        errors.append(_render_dependency_block("Unexpected extras", unexpected_extras))

    for extra_name, expected_names in sorted(expected_extras.items()):
        actual_names = actual_extras.get(extra_name, set())
        missing_names = expected_names - actual_names
        unexpected_names = actual_names - expected_names
        if missing_names:
            errors.append(
                _render_dependency_block(
                    f"Extra '{extra_name}' is missing expected requirements",
                    missing_names,
                )
            )
        if unexpected_names:
            errors.append(
                _render_dependency_block(
                    f"Extra '{extra_name}' has unexpected requirements",
                    unexpected_names,
                )
            )

    historical_tree_sitter = {
        requirement
        for requirement in actual_base
        | {name for values in actual_extras.values() for name in values}
        if requirement == "tree-sitter-typescript"
    }
    if historical_tree_sitter:
        errors.append(
            "Historical regression detected: tree-sitter-typescript should not appear in wheel metadata."
        )

    if errors:
        errors.append("Observed Requires-Dist lines:")
        errors.extend(f"  - {line}" for line in raw_requires_dist)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", nargs="+", help="Wheel file(s) to verify")
    parser.add_argument(
        "--pyproject",
        default="pyproject.toml",
        help="Path to pyproject.toml used as the source of truth",
    )
    args = parser.parse_args(argv)

    pyproject_path = Path(args.pyproject).resolve()
    wheel_paths = [Path(wheel).resolve() for wheel in args.wheel]

    exit_code = 0
    for wheel_path in wheel_paths:
        errors = verify_wheel_metadata(wheel_path, pyproject_path)
        if errors:
            exit_code = 1
            print(f"metadata-failed: {wheel_path}")
            for error in errors:
                print(error)
            continue
        print(f"metadata-ok: {wheel_path}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
