"""Quiet DroidPuppy hygiene state machine.

This module does hygiene work, not hygiene nagging. It records repo mutations,
validation commands, and compact turn/session snapshots into outputs/ so future
work can resume cleanly without yelling at the operator mid-flow.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_STATE_FILE = "droidpuppy_hygiene_state.json"
_EVENTS_FILE = "droidpuppy_hygiene_events.jsonl"
_MUTATION_TOOLS = {
    "create_file",
    "replace_in_file",
    "delete_file",
    "delete_snippet",
    "agent_run_shell_command",
}
_FILE_MUTATION_TOOLS = {
    "create_file",
    "replace_in_file",
    "delete_file",
    "delete_snippet",
}
_VALIDATION_PATTERNS = {
    "test": re.compile(
        r"\b(pytest|unittest|npm\s+test|pnpm\s+test|yarn\s+test|cargo\s+test|go\s+test)\b"
    ),
    "lint": re.compile(r"\b(ruff\s+check|eslint|flake8|mypy|pylint|cargo\s+clippy)\b"),
    "format": re.compile(r"\b(ruff\s+format|black|prettier|gofmt|cargo\s+fmt)\b"),
    "build": re.compile(
        r"\b(py_compile|tsc|npm\s+run\s+build|pnpm\s+build|cargo\s+build|go\s+build)\b"
    ),
}
_WRITEY_COMMAND_RE = re.compile(
    r"\b(ruff\s+check\s+--fix|ruff\s+format|black|prettier\s+--write|python\s+.*build_|pytest\s+.*--snapshot-update|sqlite3|alembic|npm\s+run\s+build|pnpm\s+build)\b"
)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def repo_root() -> Path:
    return Path.cwd().resolve()


def outputs_dir(root: Path | None = None) -> Path:
    target = (root or repo_root()) / "outputs"
    target.mkdir(parents=True, exist_ok=True)
    return target


def state_path(root: Path | None = None) -> Path:
    return outputs_dir(root) / _STATE_FILE


def events_path(root: Path | None = None) -> Path:
    return outputs_dir(root) / _EVENTS_FILE


@dataclass
class HygieneState:
    schema: str = "droidpuppy.hygiene_state.v1"
    mode: str = "quiet_worker"
    repo_root: str = ""
    started_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    mutation_count: int = 0
    validation_count: int = 0
    test_count: int = 0
    lint_count: int = 0
    format_count: int = 0
    build_count: int = 0
    last_mutation_at: str = ""
    last_validation_at: str = ""
    last_test_at: str = ""
    last_lint_at: str = ""
    last_format_at: str = ""
    last_build_at: str = ""
    last_tool: str = ""
    last_command: str = ""
    dirty_since_validation: bool = False
    changed_paths: list[str] = field(default_factory=list)
    generated_artifacts: list[str] = field(default_factory=list)
    recent_events: list[dict[str, Any]] = field(default_factory=list)
    git_dirty_count: int | None = None
    line_count_warnings: list[dict[str, Any]] = field(default_factory=list)

    def compact(self) -> dict[str, Any]:
        return asdict(self)


def load_state(root: Path | None = None) -> HygieneState:
    path = state_path(root)
    if not path.exists():
        return HygieneState(repo_root=str((root or repo_root()).resolve()))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return HygieneState(repo_root=str((root or repo_root()).resolve()))
    allowed = {field.name for field in HygieneState.__dataclass_fields__.values()}
    kwargs = {key: value for key, value in data.items() if key in allowed}
    kwargs.setdefault("repo_root", str((root or repo_root()).resolve()))
    return HygieneState(**kwargs)


def save_state(state: HygieneState, root: Path | None = None) -> None:
    state.updated_at = utc_now()
    state.repo_root = str((root or repo_root()).resolve())
    state_path(root).write_text(
        json.dumps(state.compact(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def append_event(event: dict[str, Any], root: Path | None = None) -> None:
    payload = {"ts": utc_now(), **event}
    with events_path(root).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _short(value: str, limit: int = 180) -> str:
    compact = " ".join(str(value or "").split())
    return compact if len(compact) <= limit else compact[: limit - 3] + "..."


def _result_success(result: Any) -> bool:
    if isinstance(result, dict) and "success" in result:
        return bool(result.get("success"))
    if isinstance(result, dict) and "exit_code" in result:
        return int(result.get("exit_code") or 0) == 0
    if isinstance(result, str) and result.startswith("ERROR:"):
        return False
    return True


def _tool_path(tool_args: dict[str, Any]) -> str:
    for key in ("file_path", "path", "directory"):
        value = tool_args.get(key)
        if value:
            return str(value)
    return ""


def _is_generated_artifact(path_text: str) -> bool:
    path = Path(path_text)
    return "outputs" in path.parts or path.suffix in {
        ".csv",
        ".sqlite3",
        ".db",
        ".jsonl",
    }


def _git_dirty_count(root: Path) -> int | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return len([line for line in result.stdout.splitlines() if line.strip()])


def _line_count_warnings(root: Path, changed_paths: list[str]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for raw in changed_paths[-80:]:
        path = Path(raw)
        full = path if path.is_absolute() else root / path
        if not full.exists() or not full.is_file():
            continue
        if full.suffix not in {".py", ".js", ".ts", ".tsx", ".jsx", ".md"}:
            continue
        try:
            lines = sum(1 for _ in full.open("r", encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        if lines >= 550:
            warnings.append({"path": str(path), "lines": lines, "threshold": 600})
    return warnings[-20:]


def _classify_validation(command: str) -> set[str]:
    return {
        name
        for name, pattern in _VALIDATION_PATTERNS.items()
        if pattern.search(command)
    }


def _record_recent(state: HygieneState, event: dict[str, Any]) -> None:
    state.recent_events = [*state.recent_events[-24:], event]


def record_tool_call(
    tool_name: str,
    tool_args: dict[str, Any] | None,
    result: Any,
    duration_ms: int | float | None = None,
    root: Path | None = None,
) -> HygieneState:
    """Record one tool call and update quiet hygiene state."""
    tool_args = tool_args or {}
    root = (root or repo_root()).resolve()
    success = _result_success(result)
    now = utc_now()
    with _LOCK:
        state = load_state(root)
        state.last_tool = tool_name
        command = str(tool_args.get("command") or "")
        event: dict[str, Any] = {
            "kind": "tool_call",
            "tool": tool_name,
            "success": success,
            "duration_ms": duration_ms,
        }

        if tool_name in _FILE_MUTATION_TOOLS:
            path_text = _tool_path(tool_args)
            state.mutation_count += 1
            state.last_mutation_at = now
            state.dirty_since_validation = True
            if path_text and path_text not in state.changed_paths:
                state.changed_paths.append(path_text)
            if path_text and _is_generated_artifact(path_text):
                state.generated_artifacts = [
                    *state.generated_artifacts[-49:],
                    path_text,
                ]
            event.update({"mutation": True, "path": path_text})

        if tool_name == "agent_run_shell_command":
            state.last_command = _short(command)
            validations = _classify_validation(command)
            if validations:
                state.validation_count += 1
                state.last_validation_at = now
                state.dirty_since_validation = False
                for validation in validations:
                    setattr(
                        state,
                        f"{validation}_count",
                        getattr(state, f"{validation}_count") + 1,
                    )
                    setattr(state, f"last_{validation}_at", now)
            if _WRITEY_COMMAND_RE.search(command):
                state.mutation_count += 1
                state.last_mutation_at = now
                state.dirty_since_validation = not bool(validations)
            event.update(
                {"command": _short(command), "validations": sorted(validations)}
            )

        state.git_dirty_count = _git_dirty_count(root)
        state.line_count_warnings = _line_count_warnings(root, state.changed_paths)
        _record_recent(state, event)
        append_event(event, root)
        save_state(state, root)
        return state


def record_checkpoint(kind: str, root: Path | None = None) -> HygieneState:
    """Refresh repo hygiene packet at turn/session/compaction boundaries."""
    root = (root or repo_root()).resolve()
    with _LOCK:
        state = load_state(root)
        state.git_dirty_count = _git_dirty_count(root)
        state.line_count_warnings = _line_count_warnings(root, state.changed_paths)
        event = {"kind": kind, "dirty_since_validation": state.dirty_since_validation}
        _record_recent(state, event)
        append_event(event, root)
        save_state(state, root)
        return state


def format_report(state: HygieneState) -> str:
    dirty = "yes" if state.dirty_since_validation else "no"
    git_dirty = (
        "unknown" if state.git_dirty_count is None else str(state.git_dirty_count)
    )
    warnings = (
        ", ".join(
            f"{item['path']}={item['lines']}l" for item in state.line_count_warnings[:5]
        )
        or "none"
    )
    return (
        "DroidPuppy hygiene worker\n"
        f"  mode: {state.mode}\n"
        f"  mutations: {state.mutation_count}\n"
        f"  validations: {state.validation_count} "
        f"(tests={state.test_count}, lint={state.lint_count}, format={state.format_count}, build={state.build_count})\n"
        f"  dirty since validation: {dirty}\n"
        f"  git dirty paths: {git_dirty}\n"
        f"  line-count watch: {warnings}\n"
        f"  state: outputs/{_STATE_FILE}\n"
        f"  events: outputs/{_EVENTS_FILE}"
    )


__all__ = [
    "HygieneState",
    "format_report",
    "record_checkpoint",
    "record_tool_call",
]
