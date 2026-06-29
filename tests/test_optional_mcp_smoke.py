"""Smoke tests for running without the optional MCP extra installed."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_without_mcp(script: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not existing else f"{ROOT}{os.pathsep}{existing}"
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_core_commands_import_and_help_without_mcp():
    script = r"""
import importlib.abc
import sys

class BlockMCP(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "mcp" or fullname.startswith("mcp."):
            raise ModuleNotFoundError("No module named 'mcp'")
        return None

sys.meta_path.insert(0, BlockMCP())

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
import importlib.abc
import sys

class BlockMCP(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "mcp" or fullname.startswith("mcp."):
            raise ModuleNotFoundError("No module named 'mcp'")
        return None

sys.meta_path.insert(0, BlockMCP())

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
