"""Slash command + tool registration for the repository catalog plugin."""

from __future__ import annotations

import shlex
from typing import Any, Optional

from code_puppy.callbacks import register_callback

from .tooling import (
    advertise_tools,
    register_tools_callback,
    repository_catalog_build_impl,
    repository_catalog_query_impl,
    workspace_catalog_build_impl,
)

_COMMAND = "repo-catalog"
_ALIAS = "repocatalog"


def _custom_help() -> list[tuple[str, str]]:
    return [(_COMMAND, "Build/query repo discovery artifacts")]


def _emit_build_result(result: dict[str, Any]) -> None:
    from code_puppy.messaging import emit_info, emit_success

    emit_success("Repository catalog built.")
    emit_info(f"root: {result['root']}")
    emit_info(f"catalog: {result['catalog_path']}")
    if result.get("include_repo_map"):
        emit_info(f"repo map: {result['repo_map_path']}")
    if result.get("include_code_index"):
        emit_info(f"code index: {result['code_index_path']}")
    emit_info(
        "python files: "
        f"{result['python_file_count']} | "
        f"classes: {result['class_count']} | "
        f"functions: {result['function_count']} | "
        f"errors: {result['error_count']}"
    )


def _emit_query_result(result: dict[str, Any]) -> None:
    from code_puppy.messaging import emit_info, emit_success, emit_warning

    if not result.get("matches"):
        emit_warning(f"No catalog matches for: {result['query']}")
        return

    emit_success(
        f"Found {len(result['matches'])} catalog match(es) "
        f"out of {result['total_matches']} total."
    )
    for entry in result["matches"]:
        emit_info(entry["path"])
        if entry.get("classes"):
            emit_info(f"  classes: {', '.join(entry['classes'])}")
        if entry.get("functions"):
            emit_info(f"  functions: {', '.join(entry['functions'])}")
        if entry.get("docstring_summary"):
            emit_info(f"  summary: {entry['docstring_summary']}")


def _emit_workspace_result(result: dict[str, Any]) -> None:
    from code_puppy.messaging import emit_info, emit_success

    emit_success("Workspace catalog built.")
    emit_info(f"base dir: {result['base_dir']}")
    emit_info(f"workspace map: {result['workspace_map_path']}")
    emit_info(f"workspace catalog: {result['workspace_catalog_path']}")
    emit_info(f"repos: {result['existing_repo_count']}/{result['repo_count']} present")
    if result.get("missing_repo_names"):
        emit_info(f"missing: {', '.join(result['missing_repo_names'])}")


def _handle_custom_command(command: str, name: str) -> Optional[bool]:
    if name not in {_COMMAND, _ALIAS}:
        return None

    from code_puppy.messaging import emit_error, emit_info

    tokens = shlex.split(command)
    if len(tokens) <= 1:
        _emit_build_result(repository_catalog_build_impl())
        return True

    subcommand = tokens[1].lower()
    if subcommand == "build":
        root = tokens[2] if len(tokens) > 2 else "."
        _emit_build_result(repository_catalog_build_impl(root=root))
        return True

    if subcommand == "query":
        if len(tokens) < 3:
            emit_error("Usage: /repo-catalog query <text>")
            return True
        query_text = " ".join(tokens[2:])
        result = repository_catalog_query_impl(query=query_text)
        if not result.get("ok"):
            emit_error(result.get("error", "Catalog query failed."))
            return True
        _emit_query_result(result)
        return True

    if subcommand == "workspace":
        base_dir = tokens[2] if len(tokens) > 2 else "~"
        _emit_workspace_result(workspace_catalog_build_impl(base_dir=base_dir))
        return True

    if subcommand == "help":
        emit_info("/repo-catalog [build [root] | query <text> | workspace [base-dir]]")
        return True

    emit_error("Unknown subcommand. Use /repo-catalog help")
    return True


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", advertise_tools)
register_callback("custom_command_help", _custom_help)
register_callback("custom_command", _handle_custom_command)
