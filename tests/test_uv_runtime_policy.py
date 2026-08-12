from __future__ import annotations

import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_uv_runtime_does_not_install_dependency_groups_by_default() -> None:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_file:
        project = tomllib.load(project_file)

    assert project["tool"]["uv"]["default-groups"] == []
    assert "dev" in project["dependency-groups"]
