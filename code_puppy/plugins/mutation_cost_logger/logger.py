from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any

from code_puppy.plugins.authority_gateway.audit import _audit_events_dir
from code_puppy.plugins.authority_gateway.identity import get_execution_identity

_LOG_LOCK = threading.Lock()
_STATE_LOCK = threading.Lock()
_PATCH_LOCK = threading.Lock()
_ATTEMPTS_BY_RUN: dict[str, list["MutationAttempt"]] = {}
_RUN_USAGE_BY_ID: dict[str, dict[str, int]] = {}
_MUTATION_CAPABILITY = "shell.repo.write"
_MUTATION_TOOL = "agent_run_shell_command"
_COMMIT_SHA_RE = re.compile(r"\[[^\s]+\s+([0-9a-f]{7,40})\]")
_FILES_CHANGED_RE = re.compile(r"(\d+) files? changed")


@dataclass
class MutationAttempt:
    run_id: str
    task_name: str
    cwd: str
    command: str
    started_at: str
    started_ns: int
    ended_at: str | None = None
    ended_ns: int | None = None
    elapsed_ms: int = 0
    success: bool = False
    failure_reason: str = ""
    stdout: str = ""
    stderr: str = ""
    before_status: dict[str, str] = field(default_factory=dict)
    after_status: dict[str, str] = field(default_factory=dict)


def _now() -> tuple[str, int]:
    now = dt.datetime.now(dt.timezone.utc)
    return now.isoformat(), time.time_ns()


def _log_path() -> Path:
    path = Path.cwd() / "outputs" / "mutation_cost.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _extract_usage(result: Any) -> dict[str, int]:
    try:
        usage = result.usage()
    except Exception:
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    input_tokens = int(
        getattr(usage, "input_tokens", 0) or getattr(usage, "request_tokens", 0) or 0
    )
    output_tokens = int(
        getattr(usage, "output_tokens", 0)
        or getattr(usage, "response_tokens", 0)
        or getattr(usage, "completion_tokens", 0)
        or 0
    )
    total_tokens = int(
        getattr(usage, "total_tokens", 0) or input_tokens + output_tokens
    )
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def ensure_runtime_usage_patch() -> None:
    with _PATCH_LOCK:
        from code_puppy.agents import _runtime

        current = _runtime.run_with_mcp
        if getattr(current, "_mutation_cost_logger_patch", False):
            return

        @wraps(current)
        async def _wrapped_run_with_mcp(*args: Any, **kwargs: Any) -> Any:
            result = await current(*args, **kwargs)
            run_id = get_execution_identity().run_id
            if run_id:
                with _STATE_LOCK:
                    _RUN_USAGE_BY_ID[run_id] = _extract_usage(result)
            return result

        _wrapped_run_with_mcp._mutation_cost_logger_patch = True  # type: ignore[attr-defined]
        _runtime.run_with_mcp = _wrapped_run_with_mcp


def _summarize_command(command: str) -> str:
    compact = " ".join((command or "").split())
    if len(compact) <= 120:
        return compact
    return compact[:117] + "..."


def _status_map_for_cwd(cwd: str) -> dict[str, str]:
    target = str(Path(cwd or ".").expanduser().resolve())
    try:
        result = subprocess.run(
            ["git", "-C", target, "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except Exception:
        return {}
    if result.returncode != 0:
        return {}
    status_map: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        status = line[:2]
        path = line[3:].strip()
        if path:
            status_map[path] = status
    return status_map


def _changed_path_count(
    before_status: dict[str, str], after_status: dict[str, str]
) -> int:
    changed_paths = set(before_status) ^ set(after_status)
    for path in set(before_status) & set(after_status):
        if before_status[path] != after_status[path]:
            changed_paths.add(path)
    return len(changed_paths)


def _result_success(result: Any) -> bool:
    if isinstance(result, dict) and "success" in result:
        return bool(result.get("success"))
    if hasattr(result, "success"):
        return bool(getattr(result, "success"))
    if isinstance(result, str) and result.startswith("ERROR:"):
        return False
    return True


def _failure_reason_from_result(result: Any) -> str:
    if isinstance(result, dict):
        for key in ("error_message", "error", "reason", "stderr"):
            value = str(result.get(key, "") or "").strip()
            if value:
                return value
        exit_code = result.get("exit_code")
        if exit_code not in (None, 0):
            return f"exit_code={exit_code}"
    if isinstance(result, str) and result.startswith("ERROR:"):
        return result.strip()
    return ""


def _stdout_from_result(result: Any) -> str:
    if isinstance(result, dict):
        return str(result.get("stdout", "") or "")
    return ""


def _stderr_from_result(result: Any) -> str:
    if isinstance(result, dict):
        return str(result.get("stderr", "") or "")
    return ""


def _extract_commit_sha(stdout: str) -> str | None:
    match = _COMMIT_SHA_RE.search(stdout or "")
    if match:
        return match.group(1)
    return None


def _extract_files_changed(stdout: str) -> int | None:
    match = _FILES_CHANGED_RE.search(stdout or "")
    if match:
        return int(match.group(1))
    return None


def _read_run_audit_events(run_id: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in sorted(_audit_events_dir().glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except Exception:
            continue
        details = payload.get("details")
        if not isinstance(details, dict):
            continue
        if details.get("run_id") != run_id:
            continue
        events.append(payload)
    events.sort(key=lambda item: int(item.get("timestamp_ns", 0) or 0))
    return events


def _event_matches_attempt(event: dict[str, Any], attempt: MutationAttempt) -> bool:
    if event.get("tool_name") != _MUTATION_TOOL:
        return False
    timestamp_ns = int(event.get("timestamp_ns", 0) or 0)
    end_ns = attempt.ended_ns or attempt.started_ns
    if timestamp_ns < attempt.started_ns - 1_000_000_000:
        return False
    if timestamp_ns > end_ns + 1_000_000_000:
        return False
    capability = str(event.get("capability") or "")
    lease_id = str(event.get("lease_id") or "")
    event_type = str(event.get("event_type") or "")
    return (
        capability == _MUTATION_CAPABILITY
        or bool(lease_id)
        or event_type
        in {
            "tool_blocked",
            "tool_failed",
            "lease_consumed",
        }
    )


def build_log_row(
    attempt: MutationAttempt,
    usage: dict[str, int],
    run_events: list[dict[str, Any]],
) -> dict[str, Any] | None:
    relevant_events = [
        event for event in run_events if _event_matches_attempt(event, attempt)
    ]
    if not relevant_events:
        return None

    lease_id = next(
        (
            str(event.get("lease_id"))
            for event in relevant_events
            if event.get("lease_id")
        ),
        None,
    )
    failure_reason = attempt.failure_reason or next(
        (
            str(event.get("reason", "") or "").strip()
            for event in relevant_events
            if str(event.get("event_type", "")) in {"tool_blocked", "tool_failed"}
            and str(event.get("reason", "") or "").strip()
        ),
        "",
    )
    files_changed_count = _extract_files_changed(attempt.stdout)
    if files_changed_count is None:
        files_changed_count = _changed_path_count(
            attempt.before_status,
            attempt.after_status,
        )
    success = attempt.success and not failure_reason

    return {
        "run_id": attempt.run_id,
        "lease_id": lease_id,
        "task_name": attempt.task_name,
        "started_at": attempt.started_at,
        "ended_at": attempt.ended_at or attempt.started_at,
        "elapsed_ms": int(attempt.elapsed_ms),
        "input_tokens": int(usage.get("input_tokens", 0) or 0),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
        "leases_issued": sum(
            1 for event in relevant_events if event.get("event_type") == "lease_minted"
        ),
        "leases_consumed": sum(
            1
            for event in relevant_events
            if event.get("event_type") == "lease_consumed"
        ),
        "audit_events_written": len(relevant_events),
        "files_changed_count": files_changed_count,
        "commit_sha": _extract_commit_sha(attempt.stdout),
        "success": success,
        "failure_reason": failure_reason,
    }


def _append_row(row: dict[str, Any]) -> None:
    with _LOG_LOCK:
        with _log_path().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


async def on_agent_run_start(
    agent_name: str,
    model_name: str,
    session_id: str | None = None,
) -> None:
    del agent_name, model_name
    ensure_runtime_usage_patch()
    if session_id:
        with _STATE_LOCK:
            _ATTEMPTS_BY_RUN.setdefault(session_id, [])


async def on_pre_tool_call(
    tool_name: str,
    tool_args: dict[str, Any],
    context: Any = None,
) -> None:
    del context
    if tool_name != _MUTATION_TOOL:
        return
    run_id = get_execution_identity().run_id
    if not run_id:
        return
    started_at, started_ns = _now()
    cwd = str(tool_args.get("cwd", ".") or ".")
    command = str(tool_args.get("command", "") or "")
    attempt = MutationAttempt(
        run_id=run_id,
        task_name=_summarize_command(command),
        cwd=cwd,
        command=command,
        started_at=started_at,
        started_ns=started_ns,
        before_status=_status_map_for_cwd(cwd),
    )
    with _STATE_LOCK:
        _ATTEMPTS_BY_RUN.setdefault(run_id, []).append(attempt)


async def on_post_tool_call(
    tool_name: str,
    tool_args: dict[str, Any],
    result: Any,
    duration_ms: float,
    context: Any = None,
) -> None:
    del tool_args, context
    if tool_name != _MUTATION_TOOL:
        return
    run_id = get_execution_identity().run_id
    if not run_id:
        return
    with _STATE_LOCK:
        attempts = _ATTEMPTS_BY_RUN.get(run_id, [])
        attempt = next(
            (item for item in reversed(attempts) if item.ended_ns is None),
            None,
        )
    if attempt is None:
        return
    ended_at, ended_ns = _now()
    attempt.ended_at = ended_at
    attempt.ended_ns = ended_ns
    attempt.elapsed_ms = int(duration_ms)
    attempt.success = _result_success(result)
    attempt.failure_reason = _failure_reason_from_result(result)
    attempt.stdout = _stdout_from_result(result)
    attempt.stderr = _stderr_from_result(result)
    attempt.after_status = _status_map_for_cwd(attempt.cwd)


async def on_agent_run_end(
    agent_name: str,
    model_name: str,
    session_id: str | None = None,
    success: bool = True,
    error: Exception | None = None,
    response_text: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    del agent_name, model_name, success, error, response_text, metadata
    if not session_id:
        return
    ensure_runtime_usage_patch()
    with _STATE_LOCK:
        attempts = _ATTEMPTS_BY_RUN.pop(session_id, [])
        usage = _RUN_USAGE_BY_ID.pop(
            session_id,
            {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        )
    if not attempts:
        return
    run_events = _read_run_audit_events(session_id)
    finished_at, finished_ns = _now()
    for attempt in attempts:
        if attempt.ended_ns is None:
            attempt.ended_at = finished_at
            attempt.ended_ns = finished_ns
            attempt.failure_reason = (
                attempt.failure_reason or "agent_run_ended_before_tool_completed"
            )
        row = build_log_row(attempt, usage, run_events)
        if row is not None:
            _append_row(row)
