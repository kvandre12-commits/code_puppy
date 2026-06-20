"""Regression tests for importing core modules without optional extras."""

from __future__ import annotations

import builtins
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

    def blocked_import(name, *args, **kwargs):
        if name in blocked_modules:
            raise ModuleNotFoundError(f"No module named '{name}'")
        return real_import(name, *args, **kwargs)

    return patch("builtins.__import__", side_effect=blocked_import)


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
