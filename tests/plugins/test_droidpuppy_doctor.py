from __future__ import annotations

from code_puppy.plugins.droidpuppy_doctor import tooling


def _pass_check(name: str, detail: str = "ok") -> dict[str, str]:
    return tooling._check(name, tooling.PASS, detail)


def _healthy_inventory() -> dict[str, object]:
    return {
        "plugin_count": 2,
        "plugins": [
            {
                "name": "authority_gateway",
                "register_callbacks": True,
                "tooling": True,
                "healthy": True,
            },
            {
                "name": "project_os_supervisor",
                "register_callbacks": True,
                "tooling": True,
                "healthy": True,
            },
        ],
        "unhealthy_plugins": [],
    }


def _utility_probe() -> dict[str, object]:
    return {
        "success": True,
        "platform": {"is_android": True, "is_termux": True, "android_version": "16"},
        "commands": {
            "am": "/usr/bin/am",
            "pm": "/usr/bin/pm",
            "cmd": "/usr/bin/cmd",
            "adb": "/usr/bin/adb",
        },
    }


def _browser_probe() -> dict[str, object]:
    return {
        "success": True,
        "browsers": {
            "brave_installed": True,
            "chrome_installed": True,
            "firefox_packages": [],
        },
    }


def _cdp_probe(stdout: str) -> dict[str, object]:
    return {
        "success": True,
        "adb": {
            "installed": True,
            "devices": {
                "stdout": stdout,
            },
        },
    }


def _ui_probe() -> dict[str, object]:
    return {
        "success": True,
        "commands": {"adb": "/usr/bin/adb"},
    }


def _screen_probe() -> dict[str, object]:
    return {
        "success": True,
        "commands": {"adb": "/usr/bin/adb"},
    }


def _surface_map(result: dict[str, object]) -> dict[str, dict[str, object]]:
    surface_inventory = result["surface_inventory"]
    assert isinstance(surface_inventory, dict)
    surfaces = surface_inventory["surfaces"]
    assert isinstance(surfaces, list)
    return {surface["surface_id"]: surface for surface in surfaces}


class TestDroidPuppyDoctor:
    def test_surface_inventory_reports_ready_android_routes(self, monkeypatch):
        monkeypatch.setattr(
            tooling,
            "_check_platform",
            lambda: [
                _pass_check("android_environment"),
                _pass_check("termux_environment"),
            ],
        )
        monkeypatch.setattr(
            tooling,
            "_check_commands",
            lambda: [
                _pass_check("core_android_commands"),
                _pass_check("adb"),
                _pass_check("termux_helpers"),
            ],
        )
        monkeypatch.setattr(
            tooling,
            "_check_browsers",
            lambda: [_pass_check("browsers")],
        )
        monkeypatch.setattr(tooling, "_inventory_plugins", _healthy_inventory)
        monkeypatch.setattr(tooling, "_probe_android_utility", _utility_probe)
        monkeypatch.setattr(tooling, "_probe_android_browser", _browser_probe)
        monkeypatch.setattr(
            tooling,
            "_probe_android_cdp",
            lambda: _cdp_probe("List of devices attached\npixel-9 device usb:1-1\n"),
        )
        monkeypatch.setattr(tooling, "_probe_android_ui", _ui_probe)
        monkeypatch.setattr(tooling, "_probe_android_screen", _screen_probe)
        monkeypatch.setattr(
            tooling,
            "_check_project_os_bus",
            lambda: [_pass_check("project_os_bus_runtime")],
        )

        result = tooling.droidpuppy_doctor(deep=False)
        surfaces = _surface_map(result)
        routes = result["surface_inventory"]["capability_routes"]

        assert result["overall_status"] == "healthy"
        assert result["surface_inventory"]["connected_adb_devices"] == 1
        assert result["surface_inventory"]["summary"] == {"ready": 7, "blocked": 0}
        assert surfaces["android_core"]["availability"] == "ready"
        assert surfaces["browser_launch"]["availability"] == "ready"
        assert surfaces["browser_dom"]["availability"] == "ready"
        assert surfaces["browser_dom"]["verification"] == "inferred"
        assert surfaces["ui_automation"]["availability"] == "ready"
        assert surfaces["screen_capture"]["availability"] == "ready"
        assert surfaces["governance"]["availability"] == "ready"
        assert any(
            route["capability_id"] == "android.browser.dom.read"
            and route["preferred_surface"] == "browser_dom"
            for route in routes
        )

    def test_surface_inventory_blocks_adb_backed_routes_without_connected_device(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            tooling,
            "_check_platform",
            lambda: [
                _pass_check("android_environment"),
                _pass_check("termux_environment"),
            ],
        )
        monkeypatch.setattr(
            tooling,
            "_check_commands",
            lambda: [
                _pass_check("core_android_commands"),
                _pass_check("adb"),
                _pass_check("termux_helpers"),
            ],
        )
        monkeypatch.setattr(
            tooling,
            "_check_browsers",
            lambda: [_pass_check("browsers")],
        )
        monkeypatch.setattr(
            tooling,
            "_check_cdp",
            lambda local_port=9222: [
                tooling._check(
                    "cdp_probe",
                    tooling.WARN,
                    "no working DevTools socket",
                    "Enable Wireless debugging first.",
                )
            ],
        )
        monkeypatch.setattr(tooling, "_inventory_plugins", _healthy_inventory)
        monkeypatch.setattr(tooling, "_probe_android_utility", _utility_probe)
        monkeypatch.setattr(tooling, "_probe_android_browser", _browser_probe)
        monkeypatch.setattr(
            tooling,
            "_probe_android_cdp",
            lambda: _cdp_probe("List of devices attached\n\n"),
        )
        monkeypatch.setattr(tooling, "_probe_android_ui", _ui_probe)
        monkeypatch.setattr(tooling, "_probe_android_screen", _screen_probe)
        monkeypatch.setattr(
            tooling,
            "_check_project_os_bus",
            lambda: [_pass_check("project_os_bus_runtime")],
        )

        result = tooling.droidpuppy_doctor(deep=True, local_port=9333)
        surfaces = _surface_map(result)

        assert result["overall_status"] == "degraded"
        assert result["deep_probe_ran"] is True
        assert result["surface_inventory"]["connected_adb_devices"] == 0
        assert result["surface_inventory"]["summary"] == {"ready": 4, "blocked": 3}
        assert surfaces["browser_dom"]["availability"] == "blocked"
        assert surfaces["browser_dom"]["verification"] == "observed"
        assert (
            "no adb-connected Android device is available"
            in surfaces["browser_dom"]["blockers"]
        )
        assert surfaces["ui_automation"]["availability"] == "blocked"
        assert surfaces["screen_capture"]["availability"] == "blocked"

    def test_project_os_bus_check_warns_when_broker_is_down(self, monkeypatch):
        monkeypatch.setattr(
            tooling,
            "_probe_project_os_bus",
            lambda: {
                "success": True,
                "broker_available": False,
                "socket_path": "/tmp/project-os.sock",
                "reason": "broker unavailable: [Errno 2] No such file or directory",
            },
        )

        rows = tooling._check_project_os_bus()

        assert rows[0]["name"] == "project_os_bus_runtime"
        assert rows[0]["status"] == tooling.WARN
        assert "broker unavailable" in rows[0]["detail"]
        assert "event_bus" in rows[0]["fix"]
