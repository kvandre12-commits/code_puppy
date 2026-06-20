from __future__ import annotations

import mimetypes
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..android_intent_kit.tooling import android_intent_send
from ..android_utility_kit.tooling import android_share_text


def _run_command(args: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": True,
            "args": args,
            "exit_code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "args": args,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "error": f"command not found: {exc}",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "args": args,
            "exit_code": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "error": f"command timed out after {timeout}s",
        }


def _which(name: str) -> str | None:
    return shutil.which(name)


def android_handoff_doctor() -> dict[str, Any]:
    return {
        "success": True,
        "commands": {
            "termux-open": _which("termux-open"),
            "termux-open-url": _which("termux-open-url"),
            "am": _which("am"),
        },
        "capabilities": {
            "text_handoff": True,
            "url_handoff": bool(_which("am") or _which("termux-open-url")),
            "file_handoff": bool(_which("termux-open")),
        },
        "guidance": [
            "Use android_handoff_text for cross-app text sending or share-sheet flows.",
            "Use android_handoff_url to move a URL into a browser or another app.",
            "Use android_handoff_file for files when termux-open is available.",
        ],
    }


def android_handoff_text(
    text: str,
    subject: str = "",
    package_name: str = "",
    chooser_title: str = "",
    dry_run: bool = True,
) -> dict[str, Any]:
    if not text.strip():
        raise ValueError("text is required")

    if package_name.strip():
        string_extras = {"android.intent.extra.TEXT": text}
        if subject.strip():
            string_extras["android.intent.extra.SUBJECT"] = subject
        return {
            "success": True,
            "mode": "explicit_intent",
            "result": android_intent_send(
                action="android.intent.action.SEND",
                mime_type="text/plain",
                package_name=package_name,
                string_extras=string_extras,
                chooser_title=chooser_title,
                dry_run=dry_run,
            ),
        }

    if dry_run:
        return {
            "success": True,
            "mode": "share_fallback",
            "result": {
                "success": True,
                "dry_run": True,
                "subject": subject,
                "text_length": len(text),
                "chooser_title": chooser_title,
                "message": "Would open Android text share flow.",
            },
        }

    return {
        "success": True,
        "mode": "share_fallback",
        "result": android_share_text(text=text, subject=subject),
    }


def android_handoff_url(
    url: str,
    package_name: str = "",
    chooser_title: str = "",
    dry_run: bool = True,
) -> dict[str, Any]:
    if not url.strip():
        raise ValueError("url is required")

    result = android_intent_send(
        action="android.intent.action.VIEW",
        data_uri=url,
        package_name=package_name,
        chooser_title=chooser_title,
        dry_run=dry_run,
    )
    return {
        "success": True,
        "mode": "view_intent",
        "result": result,
    }


def android_handoff_file(
    file_path: str,
    send: bool = True,
    chooser: bool = False,
    content_type: str = "",
    dry_run: bool = True,
) -> dict[str, Any]:
    termux_open = _which("termux-open")
    if not termux_open:
        return {
            "success": False,
            "message": "termux-open is not available for file handoff",
        }

    path = Path(file_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    resolved_type = content_type.strip() or (
        mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    )

    command = [termux_open]
    command.append("--send" if send else "--view")
    if chooser:
        command.append("--chooser")
    if resolved_type:
        command.extend(["--content-type", resolved_type])
    command.append(str(path))

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "mode": "termux-open",
            "command": command,
            "file_path": str(path),
            "content_type": resolved_type,
        }

    result = _run_command(command, timeout=40)
    return {
        "success": result.get("exit_code") == 0,
        "dry_run": False,
        "mode": "termux-open",
        "command": command,
        "file_path": str(path),
        "content_type": resolved_type,
        "launcher_result": result,
    }


def android_handoff_examples() -> dict[str, Any]:
    return {
        "success": True,
        "examples": [
            {
                "name": "send_text_to_share_sheet",
                "description": "Open the Android share flow with plain text.",
                "example_args": {
                    "text": "Hello from DroidPuppy",
                    "subject": "DroidPuppy",
                    "dry_run": True,
                },
            },
            {
                "name": "send_url_to_brave",
                "description": "Hand a URL to Brave explicitly.",
                "example_args": {
                    "url": "https://example.com",
                    "package_name": "com.brave.browser",
                    "dry_run": True,
                },
            },
            {
                "name": "share_file_with_chooser",
                "description": "Share a local file through Android's chooser.",
                "example_args": {
                    "file_path": "outputs/droidpuppy_live_test_20260613T203008Z.png",
                    "send": True,
                    "chooser": True,
                    "dry_run": True,
                },
            },
        ],
        "note": "This kit moves content between apps. Use dry-run first when exploring new app flows.",
    }
