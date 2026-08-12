"""Capability audit and conservative Git upstream maintenance."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

SCHEMA = "code_puppy.upstream_maintenance.v1"
DEFAULT_INTERVAL_SECONDS = 86_400
DEFAULT_REMOTE = "origin"
DEFAULT_BRANCH = "main"
_TRUE_VALUES = {"1", "true", "yes", "on"}
RunGit = Callable[[list[str], Path], subprocess.CompletedProcess[str]]


def env_enabled(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_VALUES


def repository_root(start: Path | None = None) -> Path | None:
    candidate = (start or Path(__file__)).resolve()
    for parent in (candidate, *candidate.parents):
        if (parent / ".git").exists() and (parent / "pyproject.toml").exists():
            return parent
    return None


def state_path() -> Path:
    configured = os.environ.get("CODE_PUPPY_MAINTENANCE_STATE", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".code_puppy" / "upstream_maintenance.json"


def load_state(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def check_due(state: dict[str, Any], now: float, interval_seconds: int) -> bool:
    last_check = state.get("checked_at_unix", 0)
    try:
        return now - float(last_check) >= max(60, interval_seconds)
    except (TypeError, ValueError):
        return True


def audit_capabilities() -> dict[str, Any]:
    commands = {
        "git": shutil.which("git"),
        "rg": shutil.which("rg"),
        "proot": shutil.which("proot"),
        "adb": shutil.which("adb"),
        "uv": shutil.which("uv"),
    }
    modules = {
        "mcp": importlib.util.find_spec("mcp") is not None,
        "playwright": importlib.util.find_spec("playwright") is not None,
        "PIL": importlib.util.find_spec("PIL") is not None,
        "rapidfuzz": importlib.util.find_spec("rapidfuzz") is not None,
    }
    is_termux = "com.termux" in str(Path(sys.executable).resolve()) or bool(
        os.environ.get("TERMUX_VERSION")
    )
    required = ["git", "rg"]
    if is_termux:
        required.append("proot")
    missing_required = [name for name in required if not commands[name]]
    optional_available = sorted(name for name, present in modules.items() if present)
    optional_missing = sorted(name for name, present in modules.items() if not present)
    notes = []
    if is_termux and not modules["playwright"]:
        notes.append(
            "Playwright is optional on Android; browser launch remains available."
        )
    return {
        "commands": commands,
        "modules": modules,
        "missing_required": missing_required,
        "optional_available": optional_available,
        "optional_missing": optional_missing,
        "notes": notes,
    }


def _run_git(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )


def _git_text(run_git: RunGit, root: Path, args: list[str]) -> str:
    result = run_git(args, root)
    return result.stdout.strip() if result.returncode == 0 else ""


def inspect_repository(
    root: Path,
    *,
    remote: str = DEFAULT_REMOTE,
    branch: str = DEFAULT_BRANCH,
    run_git: RunGit = _run_git,
) -> dict[str, Any]:
    current_branch = _git_text(run_git, root, ["branch", "--show-current"])
    dirty = bool(_git_text(run_git, root, ["status", "--porcelain"]))
    head = _git_text(run_git, root, ["rev-parse", "HEAD"])
    upstream_ref = f"{remote}/{branch}"
    upstream = _git_text(run_git, root, ["rev-parse", "--verify", upstream_ref])
    ahead = behind = None
    if head and upstream:
        counts = _git_text(
            run_git,
            root,
            ["rev-list", "--left-right", "--count", f"HEAD...{upstream_ref}"],
        ).split()
        if len(counts) == 2 and all(item.isdigit() for item in counts):
            ahead, behind = map(int, counts)
    return {
        "root": str(root),
        "branch": current_branch,
        "target_branch": branch,
        "remote": remote,
        "upstream_ref": upstream_ref,
        "dirty": dirty,
        "head": head,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "update_available": bool(behind),
        "apply_eligible": bool(
            current_branch == branch
            and not dirty
            and ahead == 0
            and behind is not None
            and behind > 0
        ),
    }


def fetch_upstream(
    root: Path,
    *,
    remote: str = DEFAULT_REMOTE,
    branch: str = DEFAULT_BRANCH,
    run_git: RunGit = _run_git,
) -> tuple[bool, str]:
    result = run_git(["fetch", "--quiet", remote, branch], root)
    detail = (result.stderr or result.stdout).strip()
    return result.returncode == 0, detail


def apply_fast_forward(
    root: Path,
    repository: dict[str, Any],
    *,
    run_git: RunGit = _run_git,
) -> tuple[bool, str]:
    if not repository.get("apply_eligible"):
        return (
            False,
            "update blocked: requires clean target branch and pure fast-forward",
        )
    result = run_git(
        ["merge", "--ff-only", str(repository["upstream_ref"])],
        root,
    )
    detail = (result.stdout or result.stderr).strip()
    return result.returncode == 0, detail


def run_maintenance(
    *,
    root: Path | None = None,
    force: bool = False,
    allow_apply: bool | None = None,
    now: float | None = None,
    path: Path | None = None,
    run_git: RunGit = _run_git,
) -> dict[str, Any]:
    timestamp = time.time() if now is None else now
    output_path = path or state_path()
    previous = load_state(output_path)
    interval = int(
        os.environ.get("CODE_PUPPY_UPDATE_INTERVAL_SECONDS", DEFAULT_INTERVAL_SECONDS)
    )
    if not force and not check_due(previous, timestamp, interval):
        return {**previous, "skipped": True, "reason": "startup check throttled"}

    resolved_root = root or repository_root()
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "checked_at_unix": timestamp,
        "capabilities": audit_capabilities(),
        "skipped": False,
    }
    if resolved_root is None or shutil.which("git") is None:
        result["repository"] = {"available": False}
        save_state(output_path, result)
        return result

    remote = os.environ.get("CODE_PUPPY_UPDATE_REMOTE", DEFAULT_REMOTE).strip()
    branch = os.environ.get("CODE_PUPPY_UPDATE_BRANCH", DEFAULT_BRANCH).strip()
    fetched, fetch_detail = fetch_upstream(
        resolved_root, remote=remote, branch=branch, run_git=run_git
    )
    repository = inspect_repository(
        resolved_root, remote=remote, branch=branch, run_git=run_git
    )
    repository.update({"available": True, "fetched": fetched})
    if fetch_detail:
        repository["fetch_detail"] = fetch_detail

    should_apply = (
        env_enabled("CODE_PUPPY_AUTO_UPDATE", default=False)
        if allow_apply is None
        else allow_apply
    )
    repository["auto_apply_enabled"] = should_apply
    if should_apply and fetched and repository["update_available"]:
        applied, detail = apply_fast_forward(resolved_root, repository, run_git=run_git)
        repository.update({"applied": applied, "apply_detail": detail})
    else:
        repository["applied"] = False

    result["repository"] = repository
    save_state(output_path, result)
    return result


def format_report(result: dict[str, Any]) -> str:
    capabilities = result.get("capabilities", {})
    repository = result.get("repository", {})
    lines = ["Puppy maintenance"]
    missing = capabilities.get("missing_required", [])
    lines.append(
        f"- required tools: {'missing ' + ', '.join(missing) if missing else 'ready'}"
    )
    optional = capabilities.get("optional_missing", [])
    lines.append(
        f"- detached optional modules: {', '.join(optional) if optional else 'none'}"
    )
    if result.get("skipped"):
        lines.append("- upstream: check throttled")
    elif not repository.get("available", False):
        lines.append("- upstream: Git checkout unavailable")
    else:
        lines.append(
            f"- upstream: {repository.get('upstream_ref')} "
            f"ahead={repository.get('ahead')} behind={repository.get('behind')}"
        )
        if repository.get("dirty"):
            lines.append("- update gate: blocked by local changes")
        elif repository.get("branch") != repository.get("target_branch"):
            lines.append(
                f"- update gate: feature branch {repository.get('branch')} left untouched"
            )
        elif repository.get("applied"):
            lines.append("- update: fast-forward applied; restart Code Puppy")
        elif repository.get("update_available"):
            lines.append(
                "- update: available; set CODE_PUPPY_AUTO_UPDATE=1 to auto-apply safely"
            )
        else:
            lines.append("- update: current")
    lines.extend(f"- note: {note}" for note in capabilities.get("notes", []))
    return "\n".join(lines)
