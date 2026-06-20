"""Regression tests for importing core modules without optional extras."""

from __future__ import annotations

import builtins
import contextlib
import importlib
import sys
from collections.abc import Iterable
from unittest.mock import patch

import pytest


_MISSING = object()


def _unload_modules(module_names: Iterable[str]) -> None:
    for module_name in module_names:
        sys.modules.pop(module_name, None)
    importlib.invalidate_caches()


def _restore_modules(originals: dict[str, object], module_names: Iterable[str]) -> None:
    _unload_modules(module_names)
    for module_name, module in originals.items():
        if module is not _MISSING:
            sys.modules[module_name] = module


def _block_imports(blocked_modules: set[str]):
    real_import = builtins.__import__
    real_import_module = importlib.import_module

    def is_blocked(name: str) -> bool:
        return any(
            name == blocked_name or name.startswith(f"{blocked_name}.")
            for blocked_name in blocked_modules
        )

    def blocked_import(name, *args, **kwargs):
        if is_blocked(name):
            raise ModuleNotFoundError(name=name)
        return real_import(name, *args, **kwargs)

    def blocked_import_module(name, package=None):
        if is_blocked(name):
            raise ModuleNotFoundError(name=name)
        return real_import_module(name, package)

    @contextlib.contextmanager
    def blocker():
        with (
            patch("builtins.__import__", side_effect=blocked_import),
            patch("importlib.import_module", side_effect=blocked_import_module),
        ):
            yield

    return blocker()


def test_model_factory_imports_without_optional_provider_sdks_until_used():
    module_names = {
        "code_puppy.model_factory",
        "code_puppy.provider_identity",
        "code_puppy.claude_cache_client",
        "anthropic",
        "openai",
        "pydantic_ai.models.anthropic",
        "pydantic_ai.models.openai",
        "pydantic_ai.profiles.openai",
        "pydantic_ai.providers.anthropic",
        "pydantic_ai.providers.cerebras",
        "pydantic_ai.providers.openai",
        "pydantic_ai.providers.openrouter",
    }
    originals = {name: sys.modules.get(name, _MISSING) for name in module_names}

    try:
        _unload_modules(module_names)
        with _block_imports(module_names - {"code_puppy.model_factory"}):
            model_factory = importlib.import_module("code_puppy.model_factory")

        with _block_imports(module_names - {"code_puppy.model_factory"}):
            with pytest.raises(RuntimeError, match="optional anthropic extra"):
                model_factory._load_async_anthropic()
            with pytest.raises(RuntimeError, match="optional openai extra"):
                model_factory._load_openai_model_classes()
            with pytest.raises(RuntimeError, match="optional openai extra"):
                model_factory.make_openai_provider("openai")
    finally:
        _restore_modules(originals, module_names)


def test_mcp_modules_import_without_optional_mcp_until_used():
    module_names = {
        "code_puppy.command_line.command_handler",
        "code_puppy.command_line.core_commands",
        "code_puppy.command_line.agent_menu",
        "code_puppy.command_line.mcp_binding_menu",
        "code_puppy.agents",
        "code_puppy.agents.agent_manager",
        "code_puppy.agents.base_agent",
        "code_puppy.agents._builder",
        "code_puppy.agents._runtime",
        "code_puppy.mcp_",
        "code_puppy.mcp_.manager",
        "code_puppy.mcp_.optional",
        "mcp",
        "mcp.shared",
        "mcp.shared.exceptions",
        "pydantic_ai.mcp",
    }
    originals = {name: sys.modules.get(name, _MISSING) for name in module_names}

    try:
        _unload_modules(module_names)
        with _block_imports({"mcp", "pydantic_ai.mcp"}):
            command_handler = importlib.import_module(
                "code_puppy.command_line.command_handler"
            )
            builder = importlib.import_module("code_puppy.agents._builder")
            runtime = importlib.import_module("code_puppy.agents._runtime")
            mcp_package = importlib.import_module("code_puppy.mcp_")

            assert command_handler is not None
            assert runtime is not None
            assert builder.load_mcp_servers(agent_name="code-puppy") == []
            assert builder.reload_mcp_servers(agent_name="code-puppy") == []

            with pytest.raises(RuntimeError, match="optional mcp extra"):
                mcp_package.get_mcp_manager()
    finally:
        _restore_modules(originals, module_names)


def test_mcp_command_warns_when_optional_mcp_extra_is_missing():
    module_names = {
        "code_puppy.command_line.core_commands",
        "code_puppy.command_line.agent_menu",
        "code_puppy.command_line.mcp_binding_menu",
        "code_puppy.agents",
        "code_puppy.agents.agent_manager",
        "code_puppy.agents.base_agent",
        "code_puppy.agents._builder",
        "code_puppy.agents._runtime",
        "code_puppy.mcp_",
        "code_puppy.mcp_.manager",
        "code_puppy.mcp_.optional",
        "mcp",
        "mcp.shared",
        "mcp.shared.exceptions",
        "pydantic_ai.mcp",
    }
    originals = {name: sys.modules.get(name, _MISSING) for name in module_names}

    try:
        _unload_modules(module_names)
        with _block_imports({"mcp", "pydantic_ai.mcp"}):
            core_commands = importlib.import_module(
                "code_puppy.command_line.core_commands"
            )
            with patch(
                "code_puppy.command_line.core_commands.emit_warning"
            ) as mock_warn:
                assert core_commands.handle_mcp_command("/mcp") is True

        mock_warn.assert_called_once()
        assert "optional mcp extra" in mock_warn.call_args[0][0]
    finally:
        _restore_modules(originals, module_names)


def test_common_imports_without_rapidfuzz():
    module_names = {"code_puppy.tools.common", "rapidfuzz.distance", "rapidfuzz"}
    originals = {name: sys.modules.get(name, _MISSING) for name in module_names}

    try:
        _unload_modules(module_names)
        with _block_imports({"rapidfuzz.distance", "rapidfuzz"}):
            common = importlib.import_module("code_puppy.tools.common")

        assert common.JaroWinkler.normalized_similarity("puppy", "puppy") == 1.0
    finally:
        _restore_modules(originals, module_names)


def test_image_tools_imports_without_pillow_until_used():
    module_names = {"code_puppy.tools.image_tools", "PIL.Image", "PIL"}
    originals = {name: sys.modules.get(name, _MISSING) for name in module_names}

    try:
        _unload_modules(module_names)
        with _block_imports({"PIL.Image", "PIL"}):
            image_tools = importlib.import_module("code_puppy.tools.image_tools")

        with pytest.raises(RuntimeError, match="optional images extra"):
            image_tools._validate_and_prepare_image(b"not-an-image")
    finally:
        _restore_modules(originals, module_names)
