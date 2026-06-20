from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .bus import publish_project_os_event_best_effort
from .state import utc_now, write_json


def run_authority_daemon(max_beats: int | None = None) -> int:
    from code_puppy.plugins.authority_gateway.tooling import authority_gateway_status

    hb_raw = os.environ.get("PROJECT_OS_HEARTBEAT_PATH", "").strip()
    heartbeat_file = Path(hb_raw).expanduser().resolve() if hb_raw else None
    interval = float(os.environ.get("PROJECT_OS_HEARTBEAT_INTERVAL_SECONDS", "2") or 2)
    service_name = os.environ.get("PROJECT_OS_SERVICE_NAME", "authority-daemon")
    beat = 0
    while max_beats is None or beat < max_beats:
        beat += 1
        snapshot = authority_gateway_status()
        payload = {
            "service_name": service_name,
            "heartbeat_at": utc_now(),
            "heartbeat_unix": time.time(),
            "pid": os.getpid(),
            "beat": beat,
            "system_state": snapshot.get("system_state"),
            "summary": snapshot.get("summary"),
            "active_lease_count": snapshot.get("active_lease_count"),
            "quarantine_count": snapshot.get("quarantine_count"),
        }
        if heartbeat_file is not None:
            write_json(heartbeat_file, payload)
        publish_project_os_event_best_effort(
            "system.authority",
            "authority_heartbeat",
            source="authority_daemon",
            payload=payload,
        )
        print(json.dumps(payload, sort_keys=True), flush=True)
        time.sleep(interval)
    return 0
