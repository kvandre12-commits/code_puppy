from __future__ import annotations

from code_puppy.plugins.android_cdp_bridge import tooling


def test_discovers_pid_specific_browser_devtools_sockets_first() -> None:
    unix_table = """
0000000000000000: 00000002 00000000 00000000 0001 02     0 @chrome_devtools_remote
0000000000000000: 00000002 00000000 00010000 0001 01 12815382 @stetho_com.google.android.apps.messaging_devtools_remote
0000000000000000: 00000002 00000000 00010000 0001 01 13204451 @chrome_devtools_remote_2730
0000000000000000: 00000002 00000000 00010000 0001 01 13204452 @com.brave.browser_devtools_remote_4242
"""

    sockets = tooling._discover_browser_devtools_sockets_from_unix(unix_table)

    assert sockets == [
        "chrome_devtools_remote_2730",
        "com.brave.browser_devtools_remote_4242",
        "chrome_devtools_remote",
    ]


def test_merge_socket_candidates_deduplicates_with_discovered_first() -> None:
    merged = tooling._merge_socket_candidates(
        ["chrome_devtools_remote_2730", "chrome_devtools_remote"],
        ["chrome_devtools_remote", "com.android.chrome_devtools_remote"],
    )

    assert merged == [
        "chrome_devtools_remote_2730",
        "chrome_devtools_remote",
        "com.android.chrome_devtools_remote",
    ]


def test_trim_target_list_result_limits_probe_noise() -> None:
    targets = [{"id": str(i), "type": "page"} for i in range(30)]

    trimmed = tooling._trim_target_list_result({"success": True, "json": targets})

    assert len(trimmed["json"]) == tooling.MAX_PROBE_TARGETS
    assert trimmed["json_count"] == 30
    assert trimmed["json_truncated"] is True


def test_probe_uses_discovered_socket_before_static_candidates(monkeypatch) -> None:
    commands: list[list[str]] = []

    def fake_adb_path() -> str:
        return "adb"

    def fake_run_command(args: list[str], timeout: int = 20) -> dict:
        commands.append(args)
        if args == ["adb", "shell", "cat", "/proc/net/unix"]:
            return {
                "ok": True,
                "args": args,
                "exit_code": 0,
                "stdout": "@chrome_devtools_remote_2730\n@chrome_devtools_remote",
                "stderr": "",
            }
        return {"ok": True, "args": args, "exit_code": 0, "stdout": "", "stderr": ""}

    def fake_http_get_json(
        url: str, timeout: int = tooling.DEFAULT_HTTP_TIMEOUT
    ) -> dict:
        if url.endswith("/json/version"):
            return {
                "success": True,
                "json": {
                    "Browser": "Chrome/test",
                    "Protocol-Version": "1.3",
                    "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser",
                },
            }
        return {"success": True, "json": []}

    monkeypatch.setattr(tooling, "_adb_path", fake_adb_path)
    monkeypatch.setattr(tooling, "_run_command", fake_run_command)
    monkeypatch.setattr(tooling, "_http_get_json", fake_http_get_json)

    result = tooling.android_cdp_probe(cleanup_forward=False)

    assert result["success"] is True
    assert result["matched_socket"] == "chrome_devtools_remote_2730"
    assert result["socket_discovery"]["sockets"] == [
        "chrome_devtools_remote_2730",
        "chrome_devtools_remote",
    ]
    assert [
        "adb",
        "forward",
        "tcp:9222",
        "localabstract:chrome_devtools_remote_2730",
    ] in commands


def test_probe_falls_back_when_discovered_pid_socket_fails(monkeypatch) -> None:
    forwarded: list[str] = []

    monkeypatch.setattr(tooling, "_adb_path", lambda: "adb")

    def fake_run_command(args: list[str], timeout: int = 20) -> dict:
        if args == ["adb", "shell", "cat", "/proc/net/unix"]:
            return {
                "ok": True,
                "args": args,
                "exit_code": 0,
                "stdout": "@chrome_devtools_remote_2730\n@chrome_devtools_remote",
                "stderr": "",
            }
        if len(args) == 4 and args[1] == "forward" and args[2] == "tcp:9222":
            forwarded.append(args[3].replace("localabstract:", ""))
        return {"ok": True, "args": args, "exit_code": 0, "stdout": "", "stderr": ""}

    def fake_http_get_json(
        url: str, timeout: int = tooling.DEFAULT_HTTP_TIMEOUT
    ) -> dict:
        current_socket = forwarded[-1]
        if (
            url.endswith("/json/version")
            and current_socket == "chrome_devtools_remote_2730"
        ):
            return {"success": False, "error": "stale pid socket"}
        if url.endswith("/json/version"):
            return {
                "success": True,
                "json": {
                    "Browser": "Chrome/test",
                    "Protocol-Version": "1.3",
                    "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser",
                },
            }
        return {"success": True, "json": []}

    monkeypatch.setattr(tooling, "_run_command", fake_run_command)
    monkeypatch.setattr(tooling, "_http_get_json", fake_http_get_json)

    result = tooling.android_cdp_probe(cleanup_forward=False)

    assert result["success"] is True
    assert result["matched_socket"] == "chrome_devtools_remote"
    assert forwarded[:2] == ["chrome_devtools_remote_2730", "chrome_devtools_remote"]
    assert result["attempts"][0]["json_list"]["error"].startswith("skipped")


def test_probe_falls_back_to_static_candidates_when_discovery_fails(
    monkeypatch,
) -> None:
    forwarded: list[str] = []

    monkeypatch.setattr(tooling, "_adb_path", lambda: "adb")

    def fake_run_command(args: list[str], timeout: int = 20) -> dict:
        if args == ["adb", "shell", "cat", "/proc/net/unix"]:
            return {
                "ok": True,
                "args": args,
                "exit_code": 1,
                "stdout": "",
                "stderr": "denied",
            }
        if len(args) == 4 and args[1] == "forward" and args[2] == "tcp:9222":
            forwarded.append(args[3].replace("localabstract:", ""))
        return {"ok": True, "args": args, "exit_code": 0, "stdout": "", "stderr": ""}

    def fake_http_get_json(
        url: str, timeout: int = tooling.DEFAULT_HTTP_TIMEOUT
    ) -> dict:
        if url.endswith("/json/version"):
            return {
                "success": True,
                "json": {
                    "Browser": "Chrome/test",
                    "Protocol-Version": "1.3",
                    "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser",
                },
            }
        return {"success": True, "json": []}

    monkeypatch.setattr(tooling, "_run_command", fake_run_command)
    monkeypatch.setattr(tooling, "_http_get_json", fake_http_get_json)

    result = tooling.android_cdp_probe(cleanup_forward=False)

    assert result["success"] is True
    assert result["matched_socket"] == tooling.SOCKET_CANDIDATES[0]
    assert forwarded[0] == tooling.SOCKET_CANDIDATES[0]
    assert result["socket_discovery"]["sockets"] == []


def test_probe_skips_json_list_when_version_fails(monkeypatch) -> None:
    requested_urls: list[str] = []

    monkeypatch.setattr(tooling, "_adb_path", lambda: "adb")
    monkeypatch.setattr(
        tooling,
        "_run_command",
        lambda args, timeout=20: {
            "ok": True,
            "args": args,
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
        },
    )

    def fake_http_get_json(
        url: str, timeout: int = tooling.DEFAULT_HTTP_TIMEOUT
    ) -> dict:
        requested_urls.append(url)
        return {"success": False, "error": "timed out"}

    monkeypatch.setattr(tooling, "_http_get_json", fake_http_get_json)

    result = tooling.android_cdp_probe(socket_candidates=["dead_socket"])

    assert result["success"] is False
    assert requested_urls == ["http://127.0.0.1:9222/json/version"]
    assert result["attempts"][0]["json_list"]["error"].startswith("skipped")
