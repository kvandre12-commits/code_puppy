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


def test_playwright_is_not_a_core_dependency():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]
    optional = pyproject["project"]["optional-dependencies"]

    assert not any(dep.startswith("playwright") for dep in dependencies)
    assert any(dep.startswith("playwright") for dep in optional["browser"])


def test_core_tools_import_without_requiring_playwright():
    assert "list_files" in TOOL_REGISTRY
    assert "browser_initialize" in TOOL_REGISTRY
    assert "Playwright extra" in PLAYWRIGHT_EXTRA_MESSAGE


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
