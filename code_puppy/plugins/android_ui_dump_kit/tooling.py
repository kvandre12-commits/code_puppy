from __future__ import annotations

import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from typing import Any


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
            "stdout": completed.stdout,
            "stderr": completed.stderr,
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
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "error": f"command timed out after {timeout}s",
        }



def _adb() -> str:
    adb = shutil.which("adb")
    if not adb:
        raise RuntimeError("adb is required for android_ui_dump_kit")
    return adb



def _dump_ui_xml() -> str:
    adb = _adb()
    last_error = "uiautomator dump failed"
    for attempt in range(3):
        dump_step = _run_command(
            [adb, "shell", "uiautomator", "dump", "/sdcard/window_dump.xml"],
            timeout=40,
        )
        if dump_step.get("exit_code") == 0:
            read_step = _run_command(
                [adb, "shell", "cat", "/sdcard/window_dump.xml"],
                timeout=20,
            )
            if read_step.get("exit_code") == 0:
                xml_text = read_step.get("stdout", "").strip()
                if xml_text.startswith("<?xml") or xml_text.startswith("<hierarchy"):
                    return xml_text
                last_error = "uiautomator dump did not return valid XML"
            else:
                last_error = read_step.get("stderr") or read_step.get("stdout") or "failed to read window_dump.xml"
        else:
            last_error = dump_step.get("stderr") or dump_step.get("stdout") or "uiautomator dump failed"
        time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(last_error)



def _parse_nodes(xml_text: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    nodes: list[dict[str, Any]] = []
    index = 0
    for elem in root.iter("node"):
        nodes.append(
            {
                "index": index,
                "text": elem.attrib.get("text", ""),
                "resource_id": elem.attrib.get("resource-id", ""),
                "class_name": elem.attrib.get("class", ""),
                "package": elem.attrib.get("package", ""),
                "content_desc": elem.attrib.get("content-desc", ""),
                "clickable": elem.attrib.get("clickable", "false") == "true",
                "enabled": elem.attrib.get("enabled", "false") == "true",
                "focusable": elem.attrib.get("focusable", "false") == "true",
                "scrollable": elem.attrib.get("scrollable", "false") == "true",
                "bounds": elem.attrib.get("bounds", ""),
            }
        )
        index += 1
    return nodes



def android_ui_dump_doctor() -> dict[str, Any]:
    adb = shutil.which("adb")
    devices = _run_command([adb, "devices", "-l"], timeout=20) if adb else None
    probe = _run_command([adb, "shell", "uiautomator", "--help"], timeout=20) if adb else None
    return {
        "success": True,
        "commands": {"adb": adb},
        "adb_devices": devices,
        "uiautomator_probe": probe,
        "guidance": [
            "Keep the phone awake and unlocked when dumping UI hierarchy.",
            "Use android_ui_dump_hierarchy to inspect the current screen.",
            "Use android_ui_dump_find to search for visible text, resource IDs, or classes.",
        ],
    }



def android_ui_dump_hierarchy(
    max_nodes: int = 200,
    include_xml: bool = False,
    max_xml_chars: int = 20000,
) -> dict[str, Any]:
    xml_text = _dump_ui_xml()
    nodes = _parse_nodes(xml_text)
    sample_nodes = nodes[:max_nodes]
    return {
        "success": True,
        "node_count": len(nodes),
        "nodes_returned": len(sample_nodes),
        "nodes": sample_nodes,
        "xml": xml_text[:max_xml_chars] if include_xml else "",
        "xml_truncated": include_xml and len(xml_text) > max_xml_chars,
    }



def android_ui_dump_find(
    query: str = "",
    resource_id: str = "",
    class_name: str = "",
    clickable_only: bool = False,
    max_results: int = 50,
) -> dict[str, Any]:
    xml_text = _dump_ui_xml()
    nodes = _parse_nodes(xml_text)
    query_norm = query.strip().lower()
    resource_norm = resource_id.strip().lower()
    class_norm = class_name.strip().lower()

    matches: list[dict[str, Any]] = []
    for node in nodes:
        if clickable_only and not node["clickable"]:
            continue
        if query_norm:
            hay = " ".join(
                [
                    str(node.get("text", "")),
                    str(node.get("content_desc", "")),
                    str(node.get("resource_id", "")),
                    str(node.get("class_name", "")),
                ]
            ).lower()
            if query_norm not in hay:
                continue
        if resource_norm and resource_norm not in str(node.get("resource_id", "")).lower():
            continue
        if class_norm and class_norm not in str(node.get("class_name", "")).lower():
            continue
        matches.append(node)
        if len(matches) >= max_results:
            break

    return {
        "success": True,
        "query": query,
        "resource_id": resource_id,
        "class_name": class_name,
        "clickable_only": clickable_only,
        "match_count": len(matches),
        "matches": matches,
    }
