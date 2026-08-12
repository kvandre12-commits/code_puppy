from __future__ import annotations

import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_uv_runtime_does_not_install_dependency_groups_by_default() -> None:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_file:
        project = tomllib.load(project_file)

    assert project["tool"]["uv"]["default-groups"] == []
    assert "dev" in project["dependency-groups"]


def test_ci_explicitly_requests_test_capabilities() -> None:
    workflows = PROJECT_ROOT / ".github" / "workflows"
    ci = (workflows / "ci.yml").read_text(encoding="utf-8")
    publish = (workflows / "publish.yml").read_text(encoding="utf-8")

    assert "uv sync --group dev" in ci
    assert "uv run --no-sync pytest" in ci
    assert "uv sync --group dev --extra durable" in publish
    assert "uv run --no-sync pytest" in publish
    assert "uv run twine" not in publish
