"""Smoke tests for running without the optional MCP extra installed.

Every test runs its assertion body in a fresh subprocess with a
``sys.meta_path`` finder that hard-blocks ``mcp`` (and any ``mcp.*``
submodule), so these hold regardless of whether the *test runner's* venv
happens to have the optional extra installed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Shared preamble: install a meta-path finder that makes ``import mcp`` (and
# ``mcp.anything``) raise ModuleNotFoundError, emulating a runtime where the
# optional extra was never installed. Kept in one place so every script below
# blocks MCP identically.
_BLOCK_MCP_PREAMBLE = r"""
import importlib.abc
import sys

class BlockMCP(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "mcp" or fullname.startswith("mcp."):
            raise ModuleNotFoundError("No module named 'mcp'", name="mcp")
        return None

sys.meta_path.insert(0, BlockMCP())
"""


def _run_without_mcp(script: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not existing else f"{ROOT}{os.pathsep}{existing}"
    return subprocess.run(
        [sys.executable, "-c", _BLOCK_MCP_PREAMBLE + script],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_core_commands_import_and_help_without_mcp():
    script = r"""
import code_puppy.messaging as messaging
import code_puppy.command_line.core_commands as core_commands

captured = []
messaging.emit_info = lambda *args, **kwargs: captured.append(str(args[0]))
core_commands.handle_help_command("/help")
assert captured, "help command did not emit anything"
print("help-ok")
"""
    result = _run_without_mcp(script)
    assert result.returncode == 0, result.stderr or result.stdout
    assert "help-ok" in result.stdout


def test_mcp_command_emits_install_hint_without_mcp():
    script = r"""
import code_puppy.command_line.core_commands as core_commands

captured = []
core_commands.emit_info = lambda message, *args, **kwargs: captured.append(str(message))
assert core_commands.handle_mcp_command("/mcp") is True
assert captured, "mcp command emitted no hint"
print(captured[0])
"""
    result = _run_without_mcp(script)
    assert result.returncode == 0, result.stderr or result.stdout
    assert "code-puppy[mcp]" in result.stdout
    assert "uv sync --extra mcp" in result.stdout


def test_core_modules_import_without_mcp():
    """main / cli_runner / agents (+ builder & runtime) import with MCP absent."""
    script = r"""
import code_puppy.main  # re-exports cli_runner.main_entry
import code_puppy.cli_runner
import code_puppy.agents
import code_puppy.agents._builder
import code_puppy.agents._runtime
import code_puppy.command_line.agent_menu  # bind menu is no longer eager

assert hasattr(code_puppy.main, "main_entry")
assert callable(code_puppy.cli_runner.main_entry)
print("imports-ok")
"""
    result = _run_without_mcp(script)
    assert result.returncode == 0, result.stderr or result.stdout
    assert "imports-ok" in result.stdout


def test_build_pydantic_agent_uses_empty_toolsets_without_mcp():
    """Agent construction succeeds and receives an empty MCP toolset.

    Uses an offline pydantic-ai ``TestModel`` and a minimal agent double so no
    provider config or network access is required.
    """
    script = r"""
from pydantic_ai.models.test import TestModel

from code_puppy.agents import _builder

# Offline doubles: bypass model-config resolution entirely.
_builder.load_model_with_fallback = lambda name, cfg, mg: (TestModel(), "test-model")
_builder.ModelFactory.load_config = staticmethod(lambda: {})

class FakeAgent:
    name = "fake-agent"

    def get_model_name(self):
        return "test-model"

    def get_full_system_prompt(self):
        return "You are a test."

    def get_available_tools(self):
        return []

agent = FakeAgent()
built = _builder.build_pydantic_agent(agent)
assert built is not None
assert agent._mcp_servers == [], agent._mcp_servers
# load_mcp_servers must short-circuit to [] before touching the manager.
assert _builder.load_mcp_servers(agent_name="fake-agent") == []
print("build-ok")
"""
    result = _run_without_mcp(script)
    assert result.returncode == 0, result.stderr or result.stdout
    assert "build-ok" in result.stdout


def test_explicit_mcp_action_emits_install_hint_without_mcp():
    """reload_mcp_servers (an explicit MCP action) raises the friendly hint."""
    script = r"""
from code_puppy.agents._builder import reload_mcp_servers
from code_puppy.mcp_optional import MCPUnavailableError

try:
    reload_mcp_servers()
except MCPUnavailableError as exc:
    msg = str(exc)
    assert "code-puppy[mcp]" in msg, msg
    assert "uv sync --extra mcp" in msg, msg
    print("reload-hint-ok")
else:
    raise SystemExit("expected MCPUnavailableError")
"""
    result = _run_without_mcp(script)
    assert result.returncode == 0, result.stderr or result.stdout
    assert "reload-hint-ok" in result.stdout


def test_mcp_run_error_type_is_inert_without_mcp():
    """The run-error compat type falls back to a private, never-raised class."""
    script = r"""
from code_puppy.mcp_optional import get_mcp_run_error_type

err_type = get_mcp_run_error_type()
assert issubclass(err_type, Exception)
# Fallback must not be a broad base that swallows normal runtime errors.
assert not issubclass(RuntimeError, err_type)
assert not issubclass(ValueError, err_type)
assert not issubclass(ModuleNotFoundError, err_type)
print("run-error-inert-ok")
"""
    result = _run_without_mcp(script)
    assert result.returncode == 0, result.stderr or result.stdout
    assert "run-error-inert-ok" in result.stdout


def test_unrelated_module_not_found_still_propagates():
    """A non-``mcp`` missing module must NOT be masked as MCPUnavailableError."""
    script = r"""
import code_puppy.mcp_ as mcp_package
from code_puppy.mcp_optional import MCPUnavailableError

# Point a fake export at a genuinely-missing (non-mcp) submodule.
mcp_package._EXPORTS["_FakeMissing"] = (".definitely_missing_submodule_xyz", "x")
try:
    mcp_package._FakeMissing
except ModuleNotFoundError as exc:
    assert not isinstance(exc, MCPUnavailableError), "unrelated MNFE was masked"
    assert exc.name != "mcp"
    print("propagated-ok")
else:
    raise SystemExit("expected ModuleNotFoundError to propagate")
"""
    result = _run_without_mcp(script)
    assert result.returncode == 0, result.stderr or result.stdout
    assert "propagated-ok" in result.stdout
