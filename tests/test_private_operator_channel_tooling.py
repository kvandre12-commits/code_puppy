from __future__ import annotations

import json

from code_puppy.plugins.private_operator_channel.tooling import (
    private_operator_channel_sign_request,
)


def test_sign_request_reports_required_capability_for_android_open() -> None:
    result = private_operator_channel_sign_request(
        action="android_open",
        args_json=json.dumps(
            {"target": "wifi", "dry_run": False, "lease_id": "lease-123"}
        ),
        shared_secret="secret-123",
    )
    assert result["success"] is True
    assert result["required_capability"] == "android.settings.open"
    assert result["payload"]["args"]["lease_id"] == "lease-123"
