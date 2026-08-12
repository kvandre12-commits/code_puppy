"""Build lightweight workspace-discovery artifacts across sibling repos."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .catalog_builder import (
    DEFAULT_IGNORES,
    _matches_ignore_name,
    discover_python_files,
)

DEFAULT_WORKSPACE_REPO_NAMES = [
    "code_puppy",
    "code_puppy_backup_20260617",
    "SharpEdge-System",
    "SharpEdge-Robinhood-Bridge",
    "DroidPuppy",
    "SharpEdge-Android",
    "SharpEdge-Ace",
    "SharpEdge-WMT",
    "SE-short-detector",
    "TENSION-MODEL",
]
DEFAULT_WORKSPACE_MAP_PATH = Path("WORKSPACE_MAP.txt")
DEFAULT_WORKSPACE_CATALOG_PATH = Path("outputs/workspace_catalog.json")


def _normalize_ignores(ignore_names: Iterable[str] | None) -> set[str]:
    names = {name.strip() for name in (ignore_names or DEFAULT_IGNORES) if name.strip()}
    return names or set(DEFAULT_IGNORES)


def _sorted_children(directory: Path, ignore_names: set[str]) -> list[Path]:
    children = [
        path
        for path in directory.iterdir()
        if path.exists()
        and not any(
            _matches_ignore_name(path.name, ignore_name) for ignore_name in ignore_names
        )
    ]
    return sorted(children, key=lambda path: (not path.is_dir(), path.name.casefold()))


def _render_limited_tree(
    directory: Path,
    ignore_names: set[str],
    *,
    max_depth: int,
    current_depth: int = 0,
    prefix: str = "",
) -> list[str]:
    if current_depth >= max_depth:
        return []

    children = _sorted_children(directory, ignore_names)
    lines: list[str] = []
    for index, child in enumerate(children):
        connector = "└── " if index == len(children) - 1 else "├── "
        suffix = "/" if child.is_dir() else ""
        lines.append(f"{prefix}{connector}{child.name}{suffix}")
        if child.is_dir():
            extension = "    " if index == len(children) - 1 else "│   "
            lines.extend(
                _render_limited_tree(
                    child,
                    ignore_names,
                    max_depth=max_depth,
                    current_depth=current_depth + 1,
                    prefix=prefix + extension,
                )
            )
    return lines


def _resolve_repo_names(repo_names: Iterable[str] | None) -> list[str]:
    names = [
        name.strip()
        for name in (repo_names or DEFAULT_WORKSPACE_REPO_NAMES)
        if name.strip()
    ]
    return names or list(DEFAULT_WORKSPACE_REPO_NAMES)


def build_workspace_map_text(
    base_dir: str | Path,
    repo_names: Iterable[str] | None = None,
    *,
    max_depth: int = 2,
    ignore_names: Iterable[str] | None = None,
) -> str:
    base_path = Path(base_dir).expanduser().resolve()
    ignore_set = _normalize_ignores(ignore_names)
    resolved_repo_names = _resolve_repo_names(repo_names)

    lines = [str(base_path)]
    for repo_name in resolved_repo_names:
        repo_path = base_path / repo_name
        if not repo_path.exists():
            lines.append(f"└── {repo_name}/ [missing]")
            continue
        lines.append(f"├── {repo_name}/")
        lines.extend(
            _render_limited_tree(
                repo_path,
                ignore_set,
                max_depth=max_depth,
                current_depth=0,
                prefix="│   ",
            )
        )
    return "\n".join(lines) + "\n"


def build_workspace_artifacts(
    *,
    output_root: str | Path = ".",
    base_dir: str | Path = "~",
    repo_names: Iterable[str] | None = None,
    workspace_map_path: str | Path = DEFAULT_WORKSPACE_MAP_PATH,
    workspace_catalog_path: str | Path = DEFAULT_WORKSPACE_CATALOG_PATH,
    max_depth: int = 2,
    ignore_names: Iterable[str] | None = None,
) -> dict[str, Any]:
    output_root_path = Path(output_root).resolve()
    output_root_path.mkdir(parents=True, exist_ok=True)
    base_path = Path(base_dir).expanduser().resolve()
    ignore_set = _normalize_ignores(ignore_names)
    resolved_repo_names = _resolve_repo_names(repo_names)

    workspace_map_output = output_root_path / Path(workspace_map_path)
    workspace_catalog_output = output_root_path / Path(workspace_catalog_path)
    workspace_catalog_output.parent.mkdir(parents=True, exist_ok=True)

    repos: list[dict[str, Any]] = []
    for repo_name in resolved_repo_names:
        repo_path = base_path / repo_name
        exists = repo_path.exists() and repo_path.is_dir()
        python_file_count = (
            len(discover_python_files(repo_path, ignore_set)) if exists else 0
        )
        repos.append(
            {
                "name": repo_name,
                "path": str(repo_path),
                "exists": exists,
                "python_file_count": python_file_count,
            }
        )

    workspace_map_output.write_text(
        build_workspace_map_text(
            base_path,
            resolved_repo_names,
            max_depth=max_depth,
            ignore_names=ignore_set,
        ),
        encoding="utf-8",
    )

    payload = {
        "base_dir": str(base_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ignore_names": sorted(ignore_set),
        "repo_count": len(repos),
        "existing_repo_count": sum(1 for repo in repos if repo["exists"]),
        "missing_repo_names": [repo["name"] for repo in repos if not repo["exists"]],
        "repos": repos,
    }
    workspace_catalog_output.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    return {
        "ok": True,
        "output_root": str(output_root_path),
        "base_dir": str(base_path),
        "workspace_map_path": str(workspace_map_output.relative_to(output_root_path)),
        "workspace_catalog_path": str(
            workspace_catalog_output.relative_to(output_root_path)
        ),
        "repo_count": payload["repo_count"],
        "existing_repo_count": payload["existing_repo_count"],
        "missing_repo_names": payload["missing_repo_names"],
    }
