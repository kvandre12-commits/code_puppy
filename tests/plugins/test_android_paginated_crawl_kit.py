from __future__ import annotations

import json

import pytest

from code_puppy.plugins.android_paginated_crawl_kit import register_callbacks, tooling


class TestAndroidPaginatedCrawlTooling:
    def test_examples_surface_freecash_style_plan(self):
        result = tooling.android_paginated_crawl_examples()

        assert result["success"] is True
        plan = json.loads(result["example_plan_json"])
        assert plan["artifact_prefix"] == "freecash-sample"
        assert plan["page_turns"][0]["label"] == "4"
        assert plan["item_taps"][0]["label"] == "screw-guru"

    def test_run_executes_recovery_tap_scroll_capture_sequence(self, monkeypatch):
        calls: list[tuple[str, dict]] = []

        def fake_tap(*, x: int, y: int, dry_run: bool):
            payload = {"x": x, "y": y, "dry_run": dry_run}
            calls.append(("tap", payload))
            return {"success": True, **payload}

        def fake_swipe(
            *,
            x1: int,
            y1: int,
            x2: int,
            y2: int,
            duration_ms: int,
            dry_run: bool,
        ):
            payload = {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "duration_ms": duration_ms,
                "dry_run": dry_run,
            }
            calls.append(("swipe", payload))
            return {"success": True, **payload}

        def fake_capture(*, artifact_name: str, dry_run: bool):
            payload = {"artifact_name": artifact_name, "dry_run": dry_run}
            calls.append(("capture", payload))
            return {"success": True, **payload}

        monkeypatch.setattr(tooling, "android_input_tap", fake_tap)
        monkeypatch.setattr(tooling, "android_input_swipe", fake_swipe)
        monkeypatch.setattr(tooling, "android_capture_screenshot", fake_capture)
        monkeypatch.setattr(tooling.time, "sleep", lambda _: None)

        plan = {
            "artifact_prefix": "freecash",
            "current_page_label": "2",
            "capture_current_page": True,
            "pagination_recovery_swipe": {
                "x1": 550,
                "y1": 1460,
                "x2": 550,
                "y2": 1750,
                "duration_ms": 250,
            },
            "page_turns": [{"label": "3", "x": 548, "y": 1578}],
            "scroll_passes_per_page": 2,
            "capture_swipe": {
                "x1": 550,
                "y1": 1830,
                "x2": 550,
                "y2": 1410,
                "duration_ms": 350,
            },
            "settle_ms": 50,
        }

        result = tooling.android_paginated_crawl_run(
            plan_json=json.dumps(plan),
            dry_run=False,
        )

        assert result["success"] is True
        assert result["capture_count"] == 4
        assert result["action_count"] == 4
        assert [kind for kind, _ in calls] == [
            "capture",
            "swipe",
            "tap",
            "capture",
            "swipe",
            "capture",
            "swipe",
            "capture",
        ]
        assert result["captures"][0]["artifact_name"] == "freecash_2_top"
        assert result["captures"][1]["artifact_name"] == "freecash_3_top"
        assert result["captures"][2]["artifact_name"] == "freecash_3_scroll_01"
        assert result["captures"][3]["artifact_name"] == "freecash_3_scroll_02"

    def test_run_can_probe_item_detail_and_close_modal(self, monkeypatch):
        calls: list[tuple[str, dict]] = []

        def fake_tap(*, x: int, y: int, dry_run: bool):
            payload = {"x": x, "y": y, "dry_run": dry_run}
            calls.append(("tap", payload))
            return {"success": True, **payload}

        def fake_capture(*, artifact_name: str, dry_run: bool):
            payload = {"artifact_name": artifact_name, "dry_run": dry_run}
            calls.append(("capture", payload))
            return {"success": True, **payload}

        monkeypatch.setattr(tooling, "android_input_tap", fake_tap)
        monkeypatch.setattr(tooling, "android_capture_screenshot", fake_capture)
        monkeypatch.setattr(tooling.time, "sleep", lambda _: None)

        plan = {
            "artifact_prefix": "freecash",
            "current_page_label": "3",
            "capture_current_page": True,
            "item_taps": [
                {
                    "page_label": "3",
                    "label": "screw-guru",
                    "x": 472,
                    "y": 1492,
                    "capture_stage": "detail-screw-guru",
                    "close_tap": {"x": 1008, "y": 1185},
                }
            ],
            "scroll_passes_per_page": 0,
        }

        result = tooling.android_paginated_crawl_run(
            plan_json=json.dumps(plan),
            dry_run=False,
        )

        assert result["success"] is True
        assert result["capture_count"] == 2
        assert result["action_count"] == 2
        assert [kind for kind, _ in calls] == [
            "capture",
            "tap",
            "capture",
            "tap",
        ]
        assert result["captures"][1]["artifact_name"] == "freecash_3_detail-screw-guru"
        assert result["actions"][0]["kind"] == "item_tap"
        assert result["actions"][1]["kind"] == "detail_close_tap"

    def test_run_rejects_invalid_plan_json(self):
        with pytest.raises(tooling.CrawlPlanError):
            tooling.android_paginated_crawl_run(plan_json="{not json}", dry_run=True)

    def test_run_requires_capture_or_page_turn(self):
        plan = {
            "artifact_prefix": "noop",
            "capture_current_page": False,
            "page_turns": [],
        }

        with pytest.raises(tooling.CrawlPlanError):
            tooling.android_paginated_crawl_run(
                plan_json=json.dumps(plan),
                dry_run=True,
            )


class TestAndroidPaginatedCrawlPluginRegistration:
    def test_register_tools_callback_exposes_surface(self):
        specs = register_callbacks.register_tools_callback()
        names = {spec["name"] for spec in specs}
        assert names == {
            "android_paginated_crawl_doctor",
            "android_paginated_crawl_examples",
            "android_paginated_crawl_run",
        }

    def test_register_agent_tools_advertises_same_surface(self):
        advertised = register_callbacks._advertise_tools_to_agent("code-puppy")
        assert advertised == [
            "android_paginated_crawl_doctor",
            "android_paginated_crawl_examples",
            "android_paginated_crawl_run",
        ]
