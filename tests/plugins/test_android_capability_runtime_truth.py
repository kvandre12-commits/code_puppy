from __future__ import annotations

from code_puppy.plugins.android_capability_graph_kit import runtime_truth


def _doctor_payload(
    *, connected_adb_devices: int, browser_dom_ready: bool
) -> dict[str, object]:
    browser_dom_availability = "ready" if browser_dom_ready else "blocked"
    browser_dom_blockers = [] if browser_dom_ready else ["pairing_required"]
    return {
        "surface_inventory": {
            "connected_adb_devices": connected_adb_devices,
            "surfaces": [
                {
                    "surface_id": "android_core",
                    "availability": "ready",
                    "blockers": [],
                },
                {
                    "surface_id": "browser_dom",
                    "availability": browser_dom_availability,
                    "blockers": browser_dom_blockers,
                },
            ],
        }
    }


def _utility_payload(
    *,
    is_termux: bool = True,
    adb_installed: bool = True,
    clipboard_read: bool = True,
    clipboard_write: bool = True,
) -> dict[str, object]:
    return {
        "platform": {
            "is_termux": is_termux,
        },
        "commands": {
            "adb": "/usr/bin/adb" if adb_installed else None,
            "termux-clipboard-get": (
                "/usr/bin/termux-clipboard-get" if clipboard_read else None
            ),
            "termux-clipboard-set": (
                "/usr/bin/termux-clipboard-set" if clipboard_write else None
            ),
            "termux-notification": "/usr/bin/termux-notification",
        },
    }


def _notification_payload(*, local_notifications: bool = True) -> dict[str, object]:
    return {
        "posting_modes": {
            "termux_api_notification": local_notifications,
        }
    }


class TestAndroidCapabilityRuntimeTruth:
    def test_collect_runtime_evidence_captures_expected_transport_events(self):
        evidence = runtime_truth.collect_runtime_evidence(
            doctor=_doctor_payload(connected_adb_devices=0, browser_dom_ready=False),
            utility=_utility_payload(),
            notifications=_notification_payload(),
        )

        subjects = {event["subject"] for event in evidence}

        assert "termux_environment" in subjects
        assert "adb_loopback" in subjects
        assert "clipboard_bridge" in subjects
        assert "browser_cdp" in subjects

    def test_build_runtime_truth_compiles_latest_transport_state(self):
        evidence = [
            runtime_truth.create_evidence_event(
                "binary_check",
                "adb",
                "SUCCESS",
                "binary found at /usr/bin/adb",
            ),
            runtime_truth.create_evidence_event(
                "transport_probe",
                "adb_loopback",
                "FAILED",
                "pairing_required",
            ),
            runtime_truth.create_evidence_event(
                "transport_probe",
                "clipboard_bridge",
                "SUCCESS",
                "clipboard helpers detected",
                raw_ref={"can_read": True, "can_write": True},
            ),
        ]

        truth = runtime_truth.build_runtime_truth(evidence)

        assert truth["version"] == runtime_truth.RUNTIME_TRUTH_VERSION
        assert truth["transports"]["adb_wireless"]["available"] is False
        assert truth["transports"]["adb_wireless"]["blocker"] == "pairing_required"
        assert truth["transports"]["clipboard"]["available"] is True
        assert truth["transports"]["clipboard"]["requires_user_paste"] is True
        assert (
            truth["probe_summaries"]["transport_probe.adb_loopback"]["status"]
            == "FAILED"
        )
