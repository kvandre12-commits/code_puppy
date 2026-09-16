"""Read-only Android observation tools for the Droid viewer plugin."""

from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic_ai import RunContext

SCREENSHOT_TOOL = "android_capture_screenshot"
UI_DUMP_TOOL = "android_ui_dump_hierarchy"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _adb_path() -> str | None:
    """Return the ADB executable when Droid observation support is available."""
    return shutil.which("adb")


def _run(
    command: list[str], *, timeout: int, text: bool
) -> subprocess.CompletedProcess[Any] | dict[str, Any]:
    try:
        return subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=text,
            timeout=timeout,
        )
    except FileNotFoundError:
        return _failure("adb_unavailable", "ADB is no longer available.")
    except subprocess.TimeoutExpired:
        return _failure("adb_timeout", "ADB did not respond before the timeout.")
    except OSError as exc:
        return _failure("adb_error", f"ADB could not be started: {exc}")


def _failure(error: str, message: str, **details: Any) -> dict[str, Any]:
    return {"success": False, "error": error, "message": message, **details}


def _connected_device(adb: str) -> str | dict[str, Any]:
    """Return one authorized device serial without issuing a device command."""
    command = [adb, "devices", "-l"]
    result = _run(command, timeout=15, text=True)
    if isinstance(result, dict):
        return result
    if result.returncode != 0:
        return _failure(
            "adb_devices_failed",
            "ADB could not list connected devices.",
            stderr=result.stderr.strip(),
        )

    devices = []
    for line in result.stdout.splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 2 and fields[1] == "device":
            devices.append(fields[0])
    if not devices:
        return _failure(
            "no_adb_device",
            "ADB is installed, but no authorized device is connected.",
        )
    return devices[0]


def _artifact_path(artifact_name: str) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", artifact_name).strip("._")
    if not safe_name:
        safe_name = "android_screen"
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path.home() / ".code_puppy" / "droid_observations"
    return output_dir / f"{safe_name}_{timestamp}.png"


def capture_screenshot(artifact_name: str = "android_screen") -> dict[str, Any]:
    """Capture the current Android display through an authorized ADB device."""
    adb = _adb_path()
    if adb is None:
        return _failure("adb_unavailable", "ADB is required for Droid observation.")
    device = _connected_device(adb)
    if isinstance(device, dict):
        return device

    command = [adb, "-s", device, "exec-out", "screencap", "-p"]
    result = _run(command, timeout=45, text=False)
    if isinstance(result, dict):
        return result
    stderr = result.stderr.decode("utf-8", errors="replace").strip()
    if result.returncode != 0:
        return _failure(
            "screenshot_failed", "Android screenshot capture failed.", stderr=stderr
        )
    if not result.stdout.startswith(_PNG_SIGNATURE):
        return _failure(
            "invalid_screenshot",
            "Android screenshot capture did not return a PNG image.",
            stderr=stderr,
        )

    file_path = _artifact_path(artifact_name)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(result.stdout)
    return {
        "success": True,
        "file_path": str(file_path),
        "bytes_written": len(result.stdout),
    }


def _extract_xml(output: str) -> str | None:
    starts = [
        position
        for marker in ("<?xml", "<hierarchy")
        if (position := output.find(marker)) >= 0
    ]
    if not starts:
        return None
    return output[min(starts) :].strip()


def dump_ui_hierarchy(
    max_nodes: int = 200,
    include_xml: bool = False,
    max_xml_chars: int = 20_000,
) -> dict[str, Any]:
    """Read the current Android accessibility hierarchy through ADB."""
    adb = _adb_path()
    if adb is None:
        return _failure("adb_unavailable", "ADB is required for Droid observation.")
    device = _connected_device(adb)
    if isinstance(device, dict):
        return device

    command = [adb, "-s", device, "exec-out", "uiautomator", "dump", "/dev/tty"]
    result = _run(command, timeout=45, text=True)
    if isinstance(result, dict):
        return result
    if result.returncode != 0:
        return _failure(
            "ui_dump_failed",
            "Android UI hierarchy capture failed.",
            stderr=result.stderr.strip(),
        )

    xml_text = _extract_xml(result.stdout)
    if xml_text is None:
        return _failure(
            "invalid_ui_dump",
            "Android UI hierarchy capture did not return XML.",
            stderr=result.stderr.strip(),
        )
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return _failure(
            "invalid_ui_dump", f"Android UI hierarchy XML is invalid: {exc}"
        )

    node_limit = max(1, min(int(max_nodes), 1_000))
    nodes: list[dict[str, Any]] = []
    node_count = 0
    for node_count, element in enumerate(root.iter("node"), start=1):
        if len(nodes) < node_limit:
            nodes.append(
                {
                    "text": element.attrib.get("text", ""),
                    "resource_id": element.attrib.get("resource-id", ""),
                    "class_name": element.attrib.get("class", ""),
                    "package": element.attrib.get("package", ""),
                    "content_desc": element.attrib.get("content-desc", ""),
                    "clickable": element.attrib.get("clickable", "false") == "true",
                    "enabled": element.attrib.get("enabled", "false") == "true",
                    "bounds": element.attrib.get("bounds", ""),
                }
            )

    xml_limit = max(0, min(int(max_xml_chars), 100_000))
    return {
        "success": True,
        "node_count": node_count,
        "nodes_returned": len(nodes),
        "nodes": nodes,
        "xml": xml_text[:xml_limit] if include_xml else "",
        "xml_truncated": include_xml and len(xml_text) > xml_limit,
    }


def register_android_capture_screenshot(agent: Any) -> None:
    @agent.tool
    async def android_capture_screenshot(
        context: RunContext,
        artifact_name: str = "android_screen",
    ) -> dict[str, Any]:
        del context
        return await asyncio.to_thread(capture_screenshot, artifact_name)


def register_android_ui_dump_hierarchy(agent: Any) -> None:
    @agent.tool
    async def android_ui_dump_hierarchy(
        context: RunContext,
        max_nodes: int = 200,
        include_xml: bool = False,
        max_xml_chars: int = 20_000,
    ) -> dict[str, Any]:
        del context
        return await asyncio.to_thread(
            dump_ui_hierarchy,
            max_nodes,
            include_xml,
            max_xml_chars,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    """Define observation tools only when their ADB transport exists."""
    if _adb_path() is None:
        return []
    return [
        {"name": SCREENSHOT_TOOL, "register_func": register_android_capture_screenshot},
        {"name": UI_DUMP_TOOL, "register_func": register_android_ui_dump_hierarchy},
    ]
