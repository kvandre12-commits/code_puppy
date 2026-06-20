"""Android App Doctor: catch misbehaving apps and explain the fix + why.

Pulls logcat (or accepts pasted log text), parses Java/Kotlin crashes, ANRs,
and native fatal signals into structured incidents, then runs each through the
knowledge base to produce a plain-English diagnosis a developer can act on:

    here's the line  ->  here's the fix  ->  here's WHY

DRY: reuses the same adb/logcat invocation style as android_logcat_kit.
Fail-soft: never raises into the agent loop.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import Any

from .knowledge import ANR_DIAG, NATIVE_DIAG, diagnose

_EXC_RE = re.compile(r"^([a-zA-Z][\w.$]*(?:Exception|Error|Throwable))(?::\s*(.*))?$")
_PROC_RE = re.compile(r"Process:\s*([\w.]+)")
_FRAME_RE = re.compile(r"^at\s+([\w.$]+)\.([\w$<>]+)\(([^)]*)\)")
_FRAMEWORK = (
    "android.",
    "java.",
    "javax.",
    "kotlin.",
    "kotlinx.",
    "androidx.",
    "com.android.",
    "dalvik.",
    "libcore.",
    "sun.",
)


def _pull_logcat(lines: int, use_adb: bool, package: str) -> dict[str, Any]:
    adb = shutil.which("adb")
    local = shutil.which("logcat")
    if use_adb and adb:
        cmd = [adb, "logcat"]
    elif local:
        cmd = [local]
    else:
        return {"ok": False, "text": "", "error": "no adb or logcat available"}
    try:
        res = subprocess.run(
            cmd + ["-d", "-v", "threadtime", "-t", str(lines)],
            capture_output=True,
            text=True,
            timeout=40,
            check=False,
        )
        return {
            "ok": res.returncode == 0,
            "text": res.stdout,
            "error": res.stderr.strip(),
        }
    except Exception as exc:  # noqa: BLE001 - fail soft
        return {"ok": False, "text": "", "error": str(exc)}


def _payload(line: str) -> str:
    """Strip the threadtime prefix, return the message after 'TAG: '."""
    # e.g. '06-14 20:58:34.522 1234 1234 E AndroidRuntime: <payload>'
    idx = line.find("AndroidRuntime:")
    if idx != -1:
        return line[idx + len("AndroidRuntime:") :].strip()
    # generic: take after the last ': ' that follows a tag
    m = re.search(r"\b[EWIDV]\s+[\w.$]+:\s?(.*)$", line)
    return m.group(1).strip() if m else line.strip()


def parse_java_crashes(log_text: str) -> list[dict[str, Any]]:
    """Find FATAL EXCEPTION blocks and extract structured incidents."""
    lines = log_text.splitlines()
    incidents = []
    i = 0
    while i < len(lines):
        if "FATAL EXCEPTION" in lines[i] and "AndroidRuntime" in lines[i]:
            block = []
            j = i
            # gather contiguous AndroidRuntime lines for this crash
            while j < len(lines) and "AndroidRuntime:" in lines[j]:
                block.append(_payload(lines[j]))
                j += 1
            incidents.append(_parse_block(block))
            i = j
        else:
            i += 1
    return incidents


def _parse_block(payloads: list[str]) -> dict[str, Any]:
    package = None
    exc_type = None
    message = None
    caused_by = []
    app_frame = None
    first_frame = None

    for p in payloads:
        pm = _PROC_RE.search(p)
        if pm and not package:
            package = pm.group(1)
        if p.startswith("Caused by:"):
            caused_by.append(p[len("Caused by:") :].strip())
        em = _EXC_RE.match(p)
        if em and exc_type is None:
            exc_type = em.group(1)
            message = em.group(2) or ""
        fm = _FRAME_RE.match(p)
        if fm:
            cls, meth, loc = fm.group(1), fm.group(2), fm.group(3)
            if first_frame is None:
                first_frame = f"{cls}.{meth}({loc})"
            if app_frame is None and not cls.startswith(_FRAMEWORK):
                app_frame = f"{cls}.{meth}({loc})"

    # the root cause is the deepest "Caused by"
    root = caused_by[-1] if caused_by else None
    root_type, root_msg = exc_type, message
    if root:
        rm = _EXC_RE.match(root)
        if rm:
            root_type, root_msg = rm.group(1), rm.group(2) or ""

    diag = diagnose(root_type or exc_type or "", root_msg or message or "")
    return {
        "kind": "crash",
        "package": package,
        "exception": exc_type,
        "message": message,
        "root_cause": root,
        "offending_line": app_frame or first_frame,
        "is_app_code": app_frame is not None,
        "diagnosis": diag,
    }


def parse_anrs(log_text: str) -> list[dict[str, Any]]:
    out = []
    for line in log_text.splitlines():
        m = re.search(r"ANR in ([\w.]+)", line)
        if m:
            what, fix, why = ANR_DIAG
            out.append(
                {
                    "kind": "anr",
                    "package": m.group(1),
                    "exception": "ANR (Application Not Responding)",
                    "message": line.strip()[-200:],
                    "offending_line": None,
                    "diagnosis": {"what": what, "fix": fix, "why": why},
                }
            )
    return out


def parse_native(log_text: str) -> list[dict[str, Any]]:
    out = []
    for line in log_text.splitlines():
        if "F DEBUG" in line and ("signal" in line.lower() or "Fatal signal" in line):
            what, fix, why = NATIVE_DIAG
            out.append(
                {
                    "kind": "native",
                    "package": None,
                    "exception": "Native fatal signal",
                    "message": line.strip()[-200:],
                    "offending_line": None,
                    "diagnosis": {"what": what, "fix": fix, "why": why},
                }
            )
    return out


def android_app_doctor(
    package: str = "",
    lines: int = 4000,
    use_adb: bool = True,
    log_text: str = "",
) -> dict[str, Any]:
    """Diagnose misbehaving apps from logcat (or pasted ``log_text``).

    Returns structured incidents, each with a plain-English what/fix/why so a
    developer knows the line, the change, and the reason behind it.
    """
    source = "pasted"
    if not log_text.strip():
        pulled = _pull_logcat(lines, use_adb, package)
        if not pulled["ok"] and not pulled["text"]:
            return {
                "success": False,
                "error": pulled.get("error", "logcat failed"),
                "incidents": [],
            }
        log_text = pulled["text"]
        source = "logcat"

    if package.strip():
        # keep crash blocks for the package, but parse full text for context
        wanted = package.strip()
    else:
        wanted = ""

    incidents = (
        parse_java_crashes(log_text) + parse_anrs(log_text) + parse_native(log_text)
    )

    if wanted:
        incidents = [
            inc
            for inc in incidents
            if (inc.get("package") or "") == wanted
            or wanted in (inc.get("message") or "")
        ]

    return {
        "success": True,
        "source": source,
        "package_filter": wanted or None,
        "incident_count": len(incidents),
        "incidents": incidents,
        "note": (
            "No crashes/ANRs found - the apps are behaving."
            if not incidents
            else f"Found {len(incidents)} incident(s). Each has what/fix/why."
        ),
    }
