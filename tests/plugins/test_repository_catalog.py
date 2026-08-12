from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from code_puppy.plugins.repository_catalog.catalog_builder import (
    build_repository_artifacts,
    query_repository_catalog,
)
from code_puppy.plugins.repository_catalog.register_callbacks import (
    _custom_help,
    _handle_custom_command,
)
from code_puppy.plugins.repository_catalog.tooling import (
    advertise_tools,
    register_tools_callback,
    workspace_catalog_build_impl,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_build_repository_artifacts_writes_all_outputs(tmp_path: Path) -> None:
    _write(
        tmp_path / "app.py",
        '"""Tiny app module."""\n\nimport os\nfrom pathlib import Path\n\n\nclass Greeter:\n    pass\n\n\ndef hello():\n    return "hi"\n',
    )
    _write(
        tmp_path / "pkg" / "worker.py",
        "from collections import defaultdict\n\n\nasync def run_job():\n    return defaultdict(list)\n",
    )
    _write(
        tmp_path / ".git" / "ignored.py",
        "def nope():\n    return False\n",
    )

    result = build_repository_artifacts(root=tmp_path)

    assert result["ok"] is True
    assert result["python_file_count"] == 2
    assert (tmp_path / "REPO_MAP.txt").exists()
    assert (tmp_path / "CODE_INDEX.txt").exists()
    assert (tmp_path / "outputs" / "repository_catalog.json").exists()

    repo_map = (tmp_path / "REPO_MAP.txt").read_text(encoding="utf-8")
    assert "app.py" in repo_map
    assert ".git" not in repo_map

    code_index = (tmp_path / "CODE_INDEX.txt").read_text(encoding="utf-8")
    assert "app.py class Greeter" in code_index
    assert "app.py def hello" in code_index
    assert "pkg/worker.py def run_job" in code_index
    assert "ignored.py" not in code_index

    payload = json.loads(
        (tmp_path / "outputs" / "repository_catalog.json").read_text(encoding="utf-8")
    )
    files = {entry["path"]: entry for entry in payload["files"]}
    assert files["app.py"]["classes"] == ["Greeter"]
    assert files["app.py"]["functions"] == ["hello"]
    assert files["app.py"]["docstring_summary"] == "Tiny app module."
    assert files["app.py"]["imports"] == ["from pathlib import Path", "import os"]
    assert files["pkg/worker.py"]["functions"] == ["run_job"]


def test_query_repository_catalog_matches_path_and_symbols(tmp_path: Path) -> None:
    _write(
        tmp_path / "alpha.py",
        '"""Alpha utilities."""\n\nclass ExecutionIdentity:\n    pass\n\n\ndef helper():\n    return 1\n',
    )
    build_repository_artifacts(
        root=tmp_path, include_repo_map=False, include_code_index=False
    )

    by_class = query_repository_catalog("ExecutionIdentity", root=tmp_path)
    assert by_class["ok"] is True
    assert by_class["total_matches"] == 1
    assert by_class["matches"][0]["path"] == "alpha.py"

    by_path = query_repository_catalog("alpha.py", root=tmp_path)
    assert by_path["total_matches"] == 1
    assert by_path["matches"][0]["functions"] == ["helper"]


def test_query_repository_catalog_requires_nonempty_query(tmp_path: Path) -> None:
    build_repository_artifacts(
        root=tmp_path, include_repo_map=False, include_code_index=False
    )
    result = query_repository_catalog("   ", root=tmp_path)
    assert result == {"ok": False, "error": "Empty query."}


def test_register_tools_callback_exposes_expected_tools() -> None:
    tool_defs = register_tools_callback()
    assert [tool_def["name"] for tool_def in tool_defs] == [
        "repository_catalog_build",
        "repository_catalog_query",
        "workspace_catalog_build",
    ]
    assert advertise_tools() == [
        "repository_catalog_build",
        "repository_catalog_query",
        "workspace_catalog_build",
    ]


def test_workspace_catalog_build_writes_workspace_outputs(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    (workspace_root / "alpha").mkdir(parents=True)
    (workspace_root / "beta").mkdir(parents=True)
    _write(workspace_root / "alpha" / "main.py", "def alpha():\n    return 1\n")
    _write(workspace_root / "beta" / "worker.py", "class Worker:\n    pass\n")

    result = workspace_catalog_build_impl(
        output_root=str(tmp_path / "artifacts"),
        base_dir=str(workspace_root),
        repo_names=["alpha", "beta", "missing"],
        max_depth=1,
    )

    assert result["ok"] is True
    assert result["existing_repo_count"] == 2
    assert result["missing_repo_names"] == ["missing"]
    assert (tmp_path / "artifacts" / "WORKSPACE_MAP.txt").exists()
    assert (tmp_path / "artifacts" / "outputs" / "workspace_catalog.json").exists()

    workspace_map = (tmp_path / "artifacts" / "WORKSPACE_MAP.txt").read_text(
        encoding="utf-8"
    )
    assert "alpha/" in workspace_map
    assert "beta/" in workspace_map
    assert "missing/ [missing]" in workspace_map


def test_custom_help_advertises_repo_catalog() -> None:
    assert _custom_help() == [("repo-catalog", "Build/query repo discovery artifacts")]


def test_handle_custom_command_builds_catalog() -> None:
    fake_result = {
        "root": "/tmp/demo",
        "catalog_path": "outputs/repository_catalog.json",
        "repo_map_path": "REPO_MAP.txt",
        "code_index_path": "CODE_INDEX.txt",
        "python_file_count": 3,
        "class_count": 2,
        "function_count": 5,
        "error_count": 0,
        "include_repo_map": True,
        "include_code_index": True,
    }
    with (
        patch(
            "code_puppy.plugins.repository_catalog.register_callbacks.repository_catalog_build_impl",
            return_value=fake_result,
        ) as mock_build,
        patch("code_puppy.messaging.emit_success") as mock_success,
        patch("code_puppy.messaging.emit_info") as mock_info,
    ):
        result = _handle_custom_command("/repo-catalog build /tmp/demo", "repo-catalog")

    assert result is True
    mock_build.assert_called_once_with(root="/tmp/demo")
    mock_success.assert_called_once()
    assert mock_info.call_count >= 3


def test_handle_custom_command_queries_catalog() -> None:
    fake_result = {
        "ok": True,
        "query": "identity",
        "total_matches": 1,
        "matches": [
            {
                "path": "code_puppy/plugins/authority_gateway/identity.py",
                "classes": ["ExecutionIdentity"],
                "functions": ["get_runtime_actor_id"],
                "docstring_summary": "Identity helpers.",
            }
        ],
    }
    with (
        patch(
            "code_puppy.plugins.repository_catalog.register_callbacks.repository_catalog_query_impl",
            return_value=fake_result,
        ) as mock_query,
        patch("code_puppy.messaging.emit_success") as mock_success,
        patch("code_puppy.messaging.emit_info") as mock_info,
    ):
        result = _handle_custom_command("/repo-catalog query identity", "repo-catalog")

    assert result is True
    mock_query.assert_called_once_with(query="identity")
    mock_success.assert_called_once()
    assert mock_info.call_count >= 1


def test_handle_custom_command_builds_workspace_catalog() -> None:
    fake_result = {
        "ok": True,
        "base_dir": "/data/data/com.termux/files/home",
        "workspace_map_path": "WORKSPACE_MAP.txt",
        "workspace_catalog_path": "outputs/workspace_catalog.json",
        "repo_count": 3,
        "existing_repo_count": 2,
        "missing_repo_names": ["SharpEdge-Android"],
    }
    with (
        patch(
            "code_puppy.plugins.repository_catalog.register_callbacks.workspace_catalog_build_impl",
            return_value=fake_result,
        ) as mock_workspace,
        patch("code_puppy.messaging.emit_success") as mock_success,
        patch("code_puppy.messaging.emit_info") as mock_info,
    ):
        result = _handle_custom_command("/repo-catalog workspace ~", "repo-catalog")

    assert result is True
    mock_workspace.assert_called_once_with(base_dir="~")
    mock_success.assert_called_once()
    assert mock_info.call_count >= 3


def test_handle_custom_command_ignores_other_commands() -> None:
    assert _handle_custom_command("/plugins", "plugins") is None
