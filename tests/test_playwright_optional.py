from __future__ import annotations

import builtins
import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest

from code_puppy.tools import TOOL_REGISTRY
from code_puppy.tools.browser.browser_manager import (
    PLAYWRIGHT_EXTRA_MESSAGE,
    BrowserManager,
)
from code_puppy.tools.image_tools import PILLOW_EXTRA_MESSAGE, _validate_and_prepare_image


def _dependency_name(requirement: str) -> str:
    name = requirement
    for separator in ("[", "<", ">", "=", ";", " "):
        name = name.split(separator, 1)[0]
    return name.lower()


def test_dependency_monsters_are_not_core_dependencies():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = {_dependency_name(dep) for dep in pyproject["project"]["dependencies"]}
    optional = pyproject["project"]["optional-dependencies"]

    assert "playwright" not in dependencies
    assert "pillow" not in dependencies
    assert "rapidfuzz" not in dependencies
    assert "ripgrep" not in dependencies

    assert any(dep.startswith("playwright") for dep in optional["browser"])
    assert any(dep.lower().startswith("pillow") for dep in optional["images"])
    assert any(dep.startswith("rapidfuzz") for dep in optional["fuzzy"])
    assert any(dep.startswith("ripgrep") for dep in optional["search"])


def test_core_tools_import_without_requiring_optional_media_deps():
    assert "list_files" in TOOL_REGISTRY
    assert "browser_initialize" in TOOL_REGISTRY
    assert "load_image_for_analysis" in TOOL_REGISTRY
    assert "Playwright extra" in PLAYWRIGHT_EXTRA_MESSAGE
    assert "images extra" in PILLOW_EXTRA_MESSAGE


def test_image_validation_explains_missing_pillow():
    with patch("code_puppy.tools.image_tools.Image", None):
        with pytest.raises(RuntimeError, match="Image loading requires"):
            _validate_and_prepare_image(b"not checked because pillow is missing")


@pytest.mark.asyncio
async def test_browser_initialize_explains_missing_playwright():
    real_import = builtins.__import__

    def block_playwright(name, *args, **kwargs):
        if name == "playwright.async_api":
            raise ModuleNotFoundError("No module named 'playwright'")
        return real_import(name, *args, **kwargs)

    manager = BrowserManager(session_id="missing-playwright-test")
    with patch("builtins.__import__", side_effect=block_playwright):
        with pytest.raises(RuntimeError, match="Browser automation requires"):
            await manager._initialize_browser()
