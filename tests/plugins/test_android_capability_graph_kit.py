from __future__ import annotations

from code_puppy.plugins.android_capability_graph_kit import tooling


def _doctor_payload(
    *, connected_adb_devices: int, browser_dom_ready: bool
) -> dict[str, object]:
    browser_dom_availability = "ready" if browser_dom_ready else "blocked"
    browser_dom_verification = "inferred" if browser_dom_ready else "observed"
    browser_dom_blockers = [] if browser_dom_ready else ["pairing_required"]
    return {
        "overall_status": "healthy" if browser_dom_ready else "degraded",
        "summary": {"pass": 6, "warn": 0 if browser_dom_ready else 1, "fail": 0},
        "deep_probe_ran": False,
        "next_steps": [] if browser_dom_ready else ["Enable Wireless Debugging."],
        "surface_inventory": {
            "connected_adb_devices": connected_adb_devices,
            "surfaces": [
                {
                    "surface_id": "android_core",
                    "label": "Android native intents and settings",
                    "availability": "ready",
                    "verification": "observed",
                    "capability_ids": [
                        "android.app.launch",
                        "android.settings.open",
                        "android.intent.send",
                    ],
                    "recommended_tools": ["android_launch_app", "android_intent_send"],
                    "detail": "Android core works.",
                    "blockers": [],
                },
                {
                    "surface_id": "browser_dom",
                    "label": "Browser DOM automation through CDP",
                    "availability": browser_dom_availability,
                    "verification": browser_dom_verification,
                    "capability_ids": [
                        "android.browser.dom.read",
                        "android.browser.dom.act",
                    ],
                    "recommended_tools": ["android_browser_read_page"],
                    "detail": "Browser DOM bridge.",
                    "blockers": browser_dom_blockers,
                },
            ],
            "capability_routes": [
                {
                    "capability_id": "android.app.launch",
                    "preferred_surface": "android_core",
                    "tools": ["android_launch_app", "android_open"],
                },
                {
                    "capability_id": "android.browser.dom.read",
                    "preferred_surface": "browser_dom",
                    "tools": ["android_browser_read_page"],
                },
            ],
        },
    }


def _utility_payload(
    *,
    adb_installed: bool = True,
    clipboard_read: bool = True,
    clipboard_write: bool = True,
) -> dict[str, object]:
    return {
        "platform": {
            "is_android": True,
            "is_termux": True,
            "android_version": "16",
            "manufacturer": "samsung",
            "model": "SM-S931U",
        },
        "commands": {
            "am": "/usr/bin/am",
            "pm": "/usr/bin/pm",
            "cmd": "/usr/bin/cmd",
            "adb": "/usr/bin/adb" if adb_installed else None,
            "termux-clipboard-get": (
                "/usr/bin/termux-clipboard-get" if clipboard_read else None
            ),
            "termux-clipboard-set": (
                "/usr/bin/termux-clipboard-set" if clipboard_write else None
            ),
        },
    }


def _notification_payload(*, local_notifications: bool = True) -> dict[str, object]:
    return {
        "posting_modes": {
            "termux_api_notification": local_notifications,
            "local_cmd_notification": False,
            "share_fallback": True,
        }
    }


class TestAndroidCapabilityGraphKit:
    def test_capability_graph_blocks_adb_backed_capabilities_when_unpaired(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            tooling,
            "droidpuppy_doctor",
            lambda deep=False, local_port=9222: _doctor_payload(
                connected_adb_devices=0,
                browser_dom_ready=False,
            ),
        )
        monkeypatch.setattr(tooling, "android_utility_doctor", _utility_payload)
        monkeypatch.setattr(
            tooling, "android_notification_doctor", _notification_payload
        )

        graph = tooling.android_capability_graph()
        transports = graph["environment"]["transport_states"]
        runtime_truth = graph["runtime_truth"]
        evidence_tail = graph["evidence_tail"]
        capabilities = {item["capability_id"]: item for item in graph["capabilities"]}

        assert graph["version"] == tooling.CAPABILITY_GRAPH_VERSION
        assert runtime_truth["version"] == "android.runtime_truth.v1"
        assert runtime_truth["observation_freshness"] == "live"
        assert len(evidence_tail) >= 1
        assert transports["termux"]["available"] is True
        assert transports["intent_bridge"]["available"] is True
        assert transports["clipboard"]["available"] is True
        assert transports["clipboard"]["supports_text"] is True
        assert transports["clipboard"]["supports_uri"] is False
        assert transports["clipboard"]["requires_user_paste"] is True
        assert transports["adb_wireless"]["available"] is False
        assert transports["adb_wireless"]["blocker"] == "pairing_required"
        assert transports["browser_cdp"]["available"] is False
        assert (
            runtime_truth["transports"]["adb_wireless"]["blocker"] == "pairing_required"
        )
        assert any(event["subject"] == "adb_loopback" for event in evidence_tail)
        assert capabilities["android.app.launch"]["score"] == 0.9
        assert capabilities["android.browser.dom.read"]["score"] == 0.0
        assert capabilities["android.browser.dom.read"]["reliability"] == "blocked"

    def test_capability_graph_scores_inferred_ready_browser_dom_as_conditional(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            tooling,
            "droidpuppy_doctor",
            lambda deep=False, local_port=9222: _doctor_payload(
                connected_adb_devices=1,
                browser_dom_ready=True,
            ),
        )
        monkeypatch.setattr(tooling, "android_utility_doctor", _utility_payload)
        monkeypatch.setattr(
            tooling, "android_notification_doctor", _notification_payload
        )

        graph = tooling.android_capability_graph()
        transports = graph["environment"]["transport_states"]
        runtime_truth = graph["runtime_truth"]
        capabilities = {item["capability_id"]: item for item in graph["capabilities"]}
        surfaces = {item["surface_id"]: item for item in graph["surfaces"]}

        assert transports["adb_wireless"]["available"] is True
        assert runtime_truth["transports"]["adb_wireless"]["available"] is True
        assert transports["browser_cdp"]["available"] is True
        assert transports["clipboard"]["can_read"] is True
        assert transports["clipboard"]["can_write"] is True
        assert capabilities["android.browser.dom.read"]["score"] == 0.75
        assert capabilities["android.browser.dom.read"]["reliability"] == "conditional"
        assert surfaces["browser_dom"]["context"] == "chrome_devtools_bridge"

    def test_capability_graph_reports_missing_clipboard_transport(self, monkeypatch):
        monkeypatch.setattr(
            tooling,
            "droidpuppy_doctor",
            lambda deep=False, local_port=9222: _doctor_payload(
                connected_adb_devices=1,
                browser_dom_ready=True,
            ),
        )
        monkeypatch.setattr(
            tooling,
            "android_utility_doctor",
            lambda: _utility_payload(clipboard_read=False, clipboard_write=False),
        )
        monkeypatch.setattr(
            tooling, "android_notification_doctor", _notification_payload
        )

        graph = tooling.android_capability_graph()
        clipboard = graph["environment"]["transport_states"]["clipboard"]
        runtime_truth = graph["runtime_truth"]

        assert clipboard["available"] is False
        assert runtime_truth["transports"]["clipboard"]["available"] is False
        assert clipboard["blocker"] == "termux_clipboard_unavailable"
        assert clipboard["supports_text"] is False
        assert clipboard["requires_user_paste"] is False
