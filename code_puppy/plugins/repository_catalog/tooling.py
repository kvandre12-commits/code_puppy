"""Agent tools for building and querying the repository catalog."""

from __future__ import annotations

from typing import Any, Iterable

from pydantic_ai import RunContext

from .catalog_builder import build_repository_artifacts, query_repository_catalog
from .workspace_builder import build_workspace_artifacts

_BUILD_TOOL = "repository_catalog_build"
_QUERY_TOOL = "repository_catalog_query"
_WORKSPACE_BUILD_TOOL = "workspace_catalog_build"


def _clean_ignores(ignore_names: Iterable[str] | None) -> list[str] | None:
    if not ignore_names:
        return None
    cleaned = [name.strip() for name in ignore_names if name and name.strip()]
    return cleaned or None


def repository_catalog_build_impl(
    *,
    root: str = ".",
    include_repo_map: bool = True,
    include_code_index: bool = True,
    ignore_names: Iterable[str] | None = None,
) -> dict[str, Any]:
    return build_repository_artifacts(
        root=root or ".",
        include_repo_map=include_repo_map,
        include_code_index=include_code_index,
        ignore_names=_clean_ignores(ignore_names),
    )


def repository_catalog_query_impl(
    *,
    query: str,
    root: str = ".",
    catalog_path: str = "outputs/repository_catalog.json",
    limit: int = 20,
) -> dict[str, Any]:
    return query_repository_catalog(
        query=query,
        root=root or ".",
        catalog_path=catalog_path,
        limit=limit,
    )


def register_repository_catalog_build(agent: Any) -> None:
    @agent.tool
    async def repository_catalog_build(
        context: RunContext,
        root: str = ".",
        include_repo_map: bool = True,
        include_code_index: bool = True,
        ignore_names: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build lightweight repo-discovery artifacts without modifying source files."""
        del context
        return repository_catalog_build_impl(
            root=root,
            include_repo_map=include_repo_map,
            include_code_index=include_code_index,
            ignore_names=ignore_names,
        )


def workspace_catalog_build_impl(
    *,
    output_root: str = ".",
    base_dir: str = "~",
    repo_names: list[str] | None = None,
    max_depth: int = 2,
    ignore_names: Iterable[str] | None = None,
) -> dict[str, Any]:
    return build_workspace_artifacts(
        output_root=output_root or ".",
        base_dir=base_dir or "~",
        repo_names=repo_names,
        max_depth=max_depth,
        ignore_names=_clean_ignores(ignore_names),
    )


def register_repository_catalog_query(agent: Any) -> None:
    @agent.tool
    async def repository_catalog_query(
        context: RunContext,
        query: str,
        root: str = ".",
        catalog_path: str = "outputs/repository_catalog.json",
        limit: int = 20,
    ) -> dict[str, Any]:
        """Query a previously-built repository catalog instead of re-walking the repo."""
        del context
        return repository_catalog_query_impl(
            query=query,
            root=root,
            catalog_path=catalog_path,
            limit=limit,
        )


def register_workspace_catalog_build(agent: Any) -> None:
    @agent.tool
    async def workspace_catalog_build(
        context: RunContext,
        output_root: str = ".",
        base_dir: str = "~",
        repo_names: list[str] | None = None,
        max_depth: int = 2,
        ignore_names: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build a lightweight workspace map/catalog across sibling repos."""
        del context
        return workspace_catalog_build_impl(
            output_root=output_root,
            base_dir=base_dir,
            repo_names=repo_names,
            max_depth=max_depth,
            ignore_names=ignore_names,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _BUILD_TOOL, "register_func": register_repository_catalog_build},
        {"name": _QUERY_TOOL, "register_func": register_repository_catalog_query},
        {
            "name": _WORKSPACE_BUILD_TOOL,
            "register_func": register_workspace_catalog_build,
        },
    ]


def advertise_tools(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_BUILD_TOOL, _QUERY_TOOL, _WORKSPACE_BUILD_TOOL]
