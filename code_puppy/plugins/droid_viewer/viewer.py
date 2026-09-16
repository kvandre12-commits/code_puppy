"""Tiny Droid viewer server for local Code Puppy status.

Stdlib-only on purpose. Android users do not need another dependency anvil.
"""

from __future__ import annotations

import html
import json
import os
import platform
import shutil
import threading
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs

_DEFAULT_PORT = 8765
_server: ThreadingHTTPServer | None = None
_server_thread: threading.Thread | None = None
_server_lock = threading.Lock()
_events: deque[dict[str, Any]] = deque(maxlen=200)
_events_lock = threading.Lock()

GOLDEN_LOOP = ("observe", "decide", "act", "verify", "log", "replay")


def _is_android() -> bool:
    return bool(os.environ.get("ANDROID_ROOT")) or shutil.which("am") is not None


def _command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def record_event(stage: str, message: str, data: dict[str, Any] | None = None) -> None:
    """Record a viewer event for the local live cockpit."""
    from datetime import datetime, timezone

    event = {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "stage": stage,
        "message": message,
        "data": data or {},
    }
    with _events_lock:
        _events.append(event)


def recent_events() -> list[dict[str, Any]]:
    """Return recent viewer events in insertion order."""
    with _events_lock:
        return list(_events)


def collect_workflow() -> dict[str, Any]:
    """Summarize the live golden-loop workflow for the cockpit."""
    events = recent_events()
    stage_counts = {stage: 0 for stage in GOLDEN_LOOP}
    for event in events:
        stage = event.get("stage")
        if stage in stage_counts:
            stage_counts[stage] += 1
    last_event = events[-1] if events else None
    return {
        "loop": list(GOLDEN_LOOP),
        "current_stage": last_event.get("stage") if last_event else "idle",
        "last_message": last_event.get("message")
        if last_event
        else "No workflow events yet.",
        "event_count": len(events),
        "stage_counts": stage_counts,
        "recent_events": events[-25:],
    }


def collect_status() -> dict[str, Any]:
    """Collect Droid viewer status without requiring DroidPuppy plugins."""
    from code_puppy.plugins.bridge_grants import register_callbacks as bridges

    bridge_rows = []
    for bridge in bridges._bridge_catalog():
        bridge_rows.append(
            {
                "name": bridge.name,
                "description": bridge.description,
                "scopes": list(bridge.scopes),
                "available": bridge.available,
                "connect_hint": bridge.connect_hint,
            }
        )

    return {
        "power_rule": bridges.POWER_RULE,
        "platform": {
            "android": _is_android(),
            "python": platform.python_version(),
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "commands": {
            "am": _command_exists("am"),
            "pm": _command_exists("pm"),
            "adb": _command_exists("adb"),
            "termux-open-url": _command_exists("termux-open-url"),
        },
        "bridges": bridge_rows,
        "grants": bridges._load_state().get("agents", {}),
        "audit_path": bridges._audit_file_path(),
        "audit_events": len(bridges._iter_audit_events()),
        "golden_loop": list(GOLDEN_LOOP),
        "viewer_events": len(recent_events()),
        "workflow": collect_workflow(),
    }


def _badge(ok: bool) -> str:
    css = "ok" if ok else "warn"
    text = "ready" if ok else "needs setup"
    return f'<span class="badge {css}">{text}</span>'


def render_html() -> str:
    """Render the Droid viewer dashboard."""
    status = collect_status()
    bridge_cards = []
    for bridge in status["bridges"]:
        scopes = ", ".join(html.escape(scope) for scope in bridge["scopes"])
        bridge_cards.append(
            "\n".join(
                [
                    '<section class="card">',
                    f"<h3>{html.escape(bridge['name'])} {_badge(bridge['available'])}</h3>",
                    f"<p>{html.escape(bridge['description'])}</p>",
                    f"<p><b>Scopes:</b> {scopes}</p>",
                    f"<p><b>Hint:</b> {html.escape(bridge['connect_hint'])}</p>",
                    "</section>",
                ]
            )
        )

    workflow = status["workflow"]
    grants = status["grants"] or {}
    grants_text = json.dumps(grants, indent=2, sort_keys=True)
    commands_text = json.dumps(status["commands"], indent=2, sort_keys=True)
    platform_text = json.dumps(status["platform"], indent=2, sort_keys=True)
    stage_counts_text = json.dumps(workflow["stage_counts"], indent=2, sort_keys=True)
    scope_options = "".join(
        f'<option value="{html.escape(scope)}"></option>'
        for scope in sorted(
            {scope for bridge in status["bridges"] for scope in bridge["scopes"]}
        )
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Code Puppy Droid</title>
  <style>
    :root {{ color-scheme: dark; --bg:#07111f; --card:#101d31; --ink:#eaf2ff; --muted:#9db1d0; --accent:#61dafb; --ok:#3ddc84; --warn:#ffcc66; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; padding:24px; font-family: system-ui, sans-serif; background: radial-gradient(circle at top, #12345a, var(--bg)); color:var(--ink); }}
    header {{ display:flex; gap:18px; align-items:center; margin-bottom:20px; }}
    .mascot {{ width:76px; height:76px; border-radius:22px; display:grid; place-items:center; background:linear-gradient(135deg,#30a7ff,#123c96); box-shadow:0 0 28px #30a7ff66; font-size:42px; }}
    h1 {{ margin:0; font-size:clamp(28px, 8vw, 48px); }}
    .rule {{ color:var(--accent); font-weight:800; }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap:14px; }}
    .card {{ background: color-mix(in srgb, var(--card) 88%, transparent); border:1px solid #ffffff18; border-radius:18px; padding:16px; box-shadow:0 8px 28px #0008; }}
    .badge {{ font-size:12px; border-radius:999px; padding:4px 8px; vertical-align:middle; }}
    .ok {{ background:#103d28; color:var(--ok); }} .warn {{ background:#493711; color:var(--warn); }}
    pre {{ white-space:pre-wrap; word-break:break-word; color:var(--muted); }}
    code {{ color:var(--accent); }}
    a {{ color:var(--accent); }}
    form {{ display:grid; gap:10px; grid-template-columns: 1fr 1fr auto auto; align-items:end; }}
    label {{ display:grid; gap:4px; color:var(--muted); font-size:13px; }}
    input, button {{ border-radius:12px; border:1px solid #ffffff22; padding:10px; background:#07111f; color:var(--ink); }}
    button {{ cursor:pointer; background:#123c96; font-weight:800; }}
    details {{ margin-top:18px; }}
    summary {{ cursor:pointer; color:var(--accent); font-weight:800; padding:12px 0; }}
    .events {{ max-height:360px; overflow:auto; }}
    .hero {{ border:1px solid #61dafb55; }}
    .stage {{ font-size:clamp(30px, 9vw, 62px); font-weight:900; letter-spacing:-0.04em; margin:8px 0; }}
    .muted {{ color:var(--muted); }}
  </style>
</head>
<body>
  <header>
    <div class="mascot" aria-label="retro cyber puppy"></div>
    <div>
      <h1>Code Puppy Droid</h1>
      <div class="rule">{html.escape(status["power_rule"])}</div>
      <p>Retro cyber puppy shell. Helmet/blaster art pending. Lawyers already sweating.</p>
    </div>
  </header>

  <section class="card hero">
    <h2>Workflow Monitor</h2>
    <div class="stage" id="current-stage">{html.escape(workflow["current_stage"])}</div>
    <p id="last-message">{html.escape(workflow["last_message"])}</p>
    <p><code>observe</code> -> <code>decide</code> -> <code>act</code> -> <code>verify</code> -> <code>log</code> -> <code>replay</code></p>
    <p class="muted">Workflow API: <a href="/workflow.json">/workflow.json</a> · Events: <a href="/events.json">/events.json</a></p>
  </section>

  <div class="grid">
    <section class="card"><h2>Stage Counts</h2><pre id="stage-counts">{html.escape(stage_counts_text)}</pre></section>
    <section class="card"><h2>System Snapshot</h2><p>Android: {status["platform"]["android"]}</p><p>ADB: {status["commands"]["adb"]}</p><p>Browser handoff: {status["commands"]["am"] and status["commands"]["pm"]}</p></section>
    <section class="card"><h2>Audit</h2><p>{status["audit_events"]} grant events</p><p>{status["viewer_events"]} workflow events</p><p class="muted">{html.escape(status["audit_path"])}</p></section>
  </div>

  <h2>Live Workflow Trail</h2>
  <section class="card events"><pre id="events">loading...</pre></section>

  <details>
    <summary>Advanced bridge permissions</summary>
    <section class="card">
      <h2>Grant or Revoke Scope</h2>
      <form method="post">
        <label>Agent <input name="agent" value="browser-agent" autocomplete="off"></label>
        <label>Scope <input name="scope" value="browser.read" list="scope-list" autocomplete="off"></label>
        <button formaction="/bridge/grant">Grant</button>
        <button formaction="/bridge/revoke">Revoke</button>
      </form>
      <datalist id="scope-list">{scope_options}</datalist>
    </section>
    <div class="grid">
      <section class="card"><h2>Current Grants</h2><pre>{html.escape(grants_text)}</pre></section>
      <section class="card"><h2>Platform</h2><pre>{html.escape(platform_text)}</pre></section>
      <section class="card"><h2>Droid Commands</h2><pre>{html.escape(commands_text)}</pre></section>
    </div>
    <h2>Bridges</h2>
    <div class="grid">
      {"".join(bridge_cards)}
    </div>
  </details>

  <script>
    async function refreshWorkflow() {{
      const response = await fetch('/workflow.json', {{cache: 'no-store'}});
      const workflow = await response.json();
      document.getElementById('current-stage').textContent = workflow.current_stage;
      document.getElementById('last-message').textContent = workflow.last_message;
      document.getElementById('stage-counts').textContent = JSON.stringify(workflow.stage_counts, null, 2);
      document.getElementById('events').textContent = JSON.stringify(workflow.recent_events, null, 2);
    }}
    refreshWorkflow();
    setInterval(refreshWorkflow, 2000);
  </script>
</body>
</html>"""


class _ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


class _ViewerHandler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *args: Any) -> None:
        return

    def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self._send(body, "application/json; charset=utf-8", status=status)

    def _redirect_home(self) -> None:
        self.send_response(303)
        self.send_header("Location", "/")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _read_payload(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return {}
            if not isinstance(parsed, dict):
                return {}
            return {str(key): str(value) for key, value in parsed.items()}
        parsed_form = parse_qs(raw, keep_blank_values=True)
        return {
            key: values[-1] if values else "" for key, values in parsed_form.items()
        }

    def _wants_json(self) -> bool:
        return "application/json" in self.headers.get("Accept", "")

    def _handle_bridge_mutation(self, action: str) -> None:
        from code_puppy.plugins.bridge_grants import register_callbacks as bridges

        payload = self._read_payload()
        agent_name = payload.get("agent", "").strip()
        scope = payload.get("scope", "").strip()
        if not agent_name or not scope:
            record_event("verify", "bridge mutation rejected", {"action": action})
            self._send_json(
                {"success": False, "error": "agent and scope are required"},
                status=400,
            )
            return

        if action == "grant":
            bridges.grant_scope(agent_name, scope)
        else:
            bridges.revoke_scope(agent_name, scope)
        record_event("act", f"bridge {action}", {"agent": agent_name, "scope": scope})
        record_event(
            "verify", "bridge state refreshed", {"grants": collect_status()["grants"]}
        )

        if self._wants_json():
            self._send_json(
                {
                    "success": True,
                    "action": action,
                    "agent": agent_name,
                    "scope": scope,
                    "status": collect_status(),
                }
            )
            return
        self._redirect_home()

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self._send(render_html().encode("utf-8"), "text/html; charset=utf-8")
            return
        if self.path == "/status.json":
            self._send_json(collect_status())
            return
        if self.path == "/workflow.json":
            self._send_json(collect_workflow())
            return
        if self.path == "/events.json":
            body = json.dumps(recent_events(), indent=2, sort_keys=True).encode("utf-8")
            self._send(body, "application/json; charset=utf-8")
            return
        self._send(b"not found", "text/plain; charset=utf-8", status=404)

    def do_POST(self) -> None:
        if self.path == "/bridge/grant":
            self._handle_bridge_mutation("grant")
            return
        if self.path == "/bridge/revoke":
            self._handle_bridge_mutation("revoke")
            return
        self._send_json({"success": False, "error": "not found"}, status=404)


def start_viewer(port: int = _DEFAULT_PORT) -> str:
    """Start the local Droid viewer and return its URL."""
    global _server, _server_thread
    with _server_lock:
        if _server is not None:
            return viewer_url()
        _server = _ReusableThreadingHTTPServer(("127.0.0.1", port), _ViewerHandler)
        _server_thread = threading.Thread(
            target=_server.serve_forever,
            name="code-puppy-droid-viewer",
            daemon=True,
        )
        _server_thread.start()
        url = viewer_url()
        record_event("observe", "Droid viewer started", {"url": url})
        return url


def stop_viewer() -> None:
    """Stop the local Droid viewer if it is running."""
    global _server, _server_thread
    with _server_lock:
        if _server is None:
            return
        url = viewer_url()
        _server.shutdown()
        _server.server_close()
        _server = None
        _server_thread = None
        record_event("log", "Droid viewer stopped", {"url": url})


def viewer_url() -> str:
    if _server is None:
        return ""
    host, port = _server.server_address
    return f"http://{host}:{port}/"


def is_running() -> bool:
    return _server is not None
