from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path

READONLY_SHELL_BINARIES = {
    "cat",
    "env",
    "find",
    "git",
    "grep",
    "head",
    "ls",
    "pwd",
    "pytest",
    "python",
    "ruff",
    "sed",
    "stat",
    "tail",
    "uv",
    "wc",
    "which",
}
READONLY_GIT_SUBCOMMANDS = {"branch", "diff", "log", "rev-parse", "show", "status"}
READONLY_PYTHON_MODULES = {"pytest", "ruff"}
READONLY_UV_TOOLS = {"pytest", "ruff"}
NETWORK_BINARIES = {
    "curl",
    "nc",
    "ncat",
    "ping",
    "rsync",
    "scp",
    "sftp",
    "ssh",
    "telnet",
    "wget",
}
ADB_BINARIES = {"adb"}
BLOCKED_SHELL_PATTERNS = (
    re.compile(r"(^|\s)sudo(\s|$)"),
    re.compile(r"(^|\s)su(\s|$)"),
    re.compile(r"(^|\s)rm\s+-rf\b"),
    re.compile(r"(^|\s)dd\s+"),
    re.compile(r"(^|\s)(mkfs|fdisk|parted|shutdown|reboot|poweroff)\b"),
    re.compile(r"\|\s*(sh|bash|zsh)\b"),
)


@dataclass(frozen=True)
class ShellPolicyDecision:
    blocked: bool = False
    reason: str = ""
    capability: str | None = None
    lease_required: bool = False


def _block(reason: str) -> ShellPolicyDecision:
    return ShellPolicyDecision(blocked=True, reason=reason)


def _require_lease(capability: str, reason: str) -> ShellPolicyDecision:
    return ShellPolicyDecision(
        capability=capability, lease_required=True, reason=reason
    )


def _safe_shell_segment(tokens: list[str]) -> bool:
    if not tokens:
        return True
    binary = tokens[0]
    if binary not in READONLY_SHELL_BINARIES:
        return False
    if binary == "git":
        return len(tokens) > 1 and tokens[1] in READONLY_GIT_SUBCOMMANDS
    if binary == "python":
        return (
            len(tokens) > 2
            and tokens[1] == "-m"
            and tokens[2] in READONLY_PYTHON_MODULES
        )
    if binary == "uv":
        return len(tokens) > 2 and tokens[1] == "run" and tokens[2] in READONLY_UV_TOOLS
    return True


def _looks_like_workspace_command(cwd: str) -> bool:
    if not cwd.strip():
        return False
    try:
        Path(cwd).expanduser().resolve()
    except OSError:
        return False
    return True


def _classify_shell_capability(parsed_segments: list[list[str]], cwd: str) -> str:
    binaries = {tokens[0] for tokens in parsed_segments if tokens}
    if binaries & ADB_BINARIES:
        return "adb.wireless.connect"
    if binaries & NETWORK_BINARIES:
        return "network.lan.connect"
    if _looks_like_workspace_command(cwd):
        return "shell.repo.write"
    return "shell.process.exec"


def assess_shell_command(command: str, *, cwd: str = "") -> ShellPolicyDecision:
    stripped = (command or "").strip()
    if not stripped:
        return _block("[BLOCKED] Empty shell command is not allowed.")

    for pattern in BLOCKED_SHELL_PATTERNS:
        if pattern.search(stripped):
            return _block(
                "[BLOCKED] Command matched a statically forbidden shell pattern."
            )

    chain_segments = re.split(r"\s*(?:&&|\|\||;)\s*", stripped)
    parsed_segments: list[list[str]] = []
    for segment in chain_segments:
        segment = segment.strip()
        if not segment:
            continue
        try:
            tokens = shlex.split(segment)
        except ValueError:
            return _require_lease(
                "shell.process.exec",
                "Shell command parsing failed cleanly, so a lease is required.",
            )
        parsed_segments.append(tokens)

    if parsed_segments and all(
        _safe_shell_segment(tokens) for tokens in parsed_segments
    ):
        return ShellPolicyDecision()

    capability = _classify_shell_capability(parsed_segments, cwd)
    reason_by_capability = {
        "shell.repo.write": "Workspace-mutating shell commands require an active execution lease.",
        "shell.process.exec": "General process execution requires an active execution lease.",
        "network.lan.connect": "Network-facing shell commands require an active execution lease.",
        "adb.wireless.connect": "ADB and nearby-device shell commands require an active execution lease.",
    }
    return _require_lease(capability, reason_by_capability[capability])
