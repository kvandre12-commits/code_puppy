"""Provider SDKs should remain optional for core import/config paths."""

from __future__ import annotations

import builtins
import importlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

_BLOCKED_TOP_LEVEL = {"anthropic", "azure", "boto3", "mcp", "openai"}
_BLOCKED_PREFIXES = tuple(f"{name}." for name in _BLOCKED_TOP_LEVEL)
_BLOCKED_PYDANTIC_AI_PARTS = (
    "pydantic_ai.models.anthropic",
    "pydantic_ai.models.openai",
    "pydantic_ai.providers.anthropic",
    "pydantic_ai.providers.cerebras",
    "pydantic_ai.providers.openai",
    "pydantic_ai.providers.openrouter",
)


def _is_blocked_import(name: str) -> bool:
    return (
        name in _BLOCKED_TOP_LEVEL
        or name.startswith(_BLOCKED_PREFIXES)
        or name in _BLOCKED_PYDANTIC_AI_PARTS
    )


@contextmanager
def _block_provider_imports(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    original_import = builtins.__import__

    for module_name in list(sys.modules):
        if _is_blocked_import(module_name):
            sys.modules.pop(module_name, None)

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 0 and _is_blocked_import(name):
            raise ImportError(f"blocked optional provider dependency: {name}")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    yield


def test_provider_identity_resolution_does_not_import_provider_sdks(monkeypatch):
    with _block_provider_imports(monkeypatch):
        provider_identity = importlib.import_module("code_puppy.provider_identity")

        assert (
            provider_identity.resolve_provider_identity(
                "openrouter-llama", {"type": "openrouter"}
            )
            == "openrouter"
        )


def test_model_factory_config_paths_do_not_import_provider_sdks(monkeypatch):
    with _block_provider_imports(monkeypatch):
        model_factory = importlib.import_module("code_puppy.model_factory")

        config = model_factory.ModelFactory.load_config()

        assert isinstance(config, dict)


def test_agent_builder_imports_without_mcp_bridge(monkeypatch):
    with _block_provider_imports(monkeypatch):
        builder = importlib.import_module("code_puppy.agents._builder")

        assert builder.load_mcp_servers(agent_name="tiny-install") == []


def test_mcp_command_reports_missing_extra(monkeypatch):
    with _block_provider_imports(monkeypatch):
        core_commands = importlib.import_module("code_puppy.command_line.core_commands")

        assert core_commands.handle_mcp_command("/mcp") is True


def test_missing_openai_key_skips_before_importing_openai_sdk(monkeypatch):
    with _block_provider_imports(monkeypatch):
        model_factory = importlib.import_module("code_puppy.model_factory")
        monkeypatch.setattr(model_factory, "get_api_key", lambda _key: None)

        model = model_factory.ModelFactory.get_model(
            "test-openai",
            {"test-openai": {"type": "openai", "name": "gpt-test"}},
        )

        assert model is None
