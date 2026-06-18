"""Tests for the local Droid viewer plugin."""

from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from code_puppy.plugins.bridge_grants import register_callbacks as bridge_grants
from code_puppy.plugins.droid_viewer import register_callbacks, viewer


def teardown_function():
    viewer.stop_viewer()


def _post_form(url: str, payload: dict[str, str]):
    data = urlencode(payload).encode("utf-8")
    request = Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    return urlopen(request, timeout=5)


def test_collect_status_has_power_rule_and_bridges():
    status = viewer.collect_status()

    assert status["power_rule"] == "No direct power. Only granted power."
    assert "platform" in status
    assert any(bridge["name"] == "viewer.browser" for bridge in status["bridges"])


def test_viewer_serves_status_json():
    url = viewer.start_viewer(0)

    with urlopen(f"{url}status.json", timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))

    assert payload["power_rule"] == "No direct power. Only granted power."
    assert payload["golden_loop"] == [
        "observe",
        "decide",
        "act",
        "verify",
        "log",
        "replay",
    ]
    assert payload["workflow"]["current_stage"] in {"idle", "observe", "log"}
    assert response.status == 200


def test_viewer_serves_html():
    url = viewer.start_viewer(0)

    with urlopen(url, timeout=5) as response:
        body = response.read().decode("utf-8")

    assert "Code Puppy Droid" in body
    assert "No direct power" in body
    assert "Workflow Monitor" in body
    assert "Advanced bridge permissions" in body
    assert "/bridge/grant" in body
    assert "Live Workflow Trail" in body


def test_workflow_and_events_json_record_viewer_lifecycle():
    url = viewer.start_viewer(0)

    with urlopen(f"{url}events.json", timeout=5) as response:
        events = json.loads(response.read().decode("utf-8"))
    with urlopen(f"{url}workflow.json", timeout=5) as response:
        workflow = json.loads(response.read().decode("utf-8"))

    assert any(event["message"] == "Droid viewer started" for event in events)
    assert workflow["current_stage"] == "observe"
    assert workflow["stage_counts"]["observe"] >= 1


def test_bridge_grant_and_revoke_http_endpoints(tmp_path, monkeypatch):
    grants_file = tmp_path / "bridge_grants.json"
    monkeypatch.setattr(bridge_grants, "GRANTS_FILE", str(grants_file))
    url = viewer.start_viewer(0)

    with _post_form(
        f"{url}bridge/grant",
        {"agent": "browser-agent", "scope": "browser.read"},
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))

    assert payload["success"] is True
    assert bridge_grants.has_scope("browser-agent", "browser.read")

    with _post_form(
        f"{url}bridge/revoke",
        {"agent": "browser-agent", "scope": "browser.read"},
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))

    assert payload["success"] is True
    assert not bridge_grants.has_scope("browser-agent", "browser.read")
    assert len(bridge_grants._iter_audit_events()) == 2


def test_droid_command_open_starts_viewer_without_browser(monkeypatch):
    opened: list[str] = []

    def fake_open(url: str) -> bool:
        opened.append(url)
        return True

    monkeypatch.setattr(register_callbacks, "_open_url", fake_open)

    assert register_callbacks._handle_droid_command("/droid open 8766", "droid") is True
    assert viewer.is_running()
    assert opened and opened[0].startswith("http://127.0.0.1:")


def test_non_droid_command_is_ignored():
    assert register_callbacks._handle_droid_command("/nope", "nope") is None
