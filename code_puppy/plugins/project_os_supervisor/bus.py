from __future__ import annotations

import json
import selectors
import socket
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .state import event_socket_path, utc_now

DEFAULT_QUEUE_LIMIT = 128
DEFAULT_SELECT_TIMEOUT = 0.2
DEFAULT_TAIL_SECONDS = 3.0
DEFAULT_TAIL_MAX_EVENTS = 20
DEFAULT_BUS_STATUS_TIMEOUT = 0.5


@dataclass
class _Client:
    sock: socket.socket
    in_buffer: bytearray = field(default_factory=bytearray)
    out_queue: deque[bytes] = field(default_factory=deque)
    write_offset: int = 0
    subscriptions: list[str] = field(default_factory=list)
    queue_limit: int = DEFAULT_QUEUE_LIMIT
    subscribed: bool = False


def _socket_path() -> Path:
    path = event_socket_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _json_line(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")


def _topic_matches(topic: str, subscriptions: list[str]) -> bool:
    if not subscriptions:
        return True
    for item in subscriptions:
        token = item.strip()
        if not token or token == "*":
            return True
        if token.endswith("*"):
            if topic.startswith(token[:-1]):
                return True
        elif topic == token or topic.startswith(token):
            return True
    return False


def _enqueue(client: _Client, payload: dict[str, Any]) -> None:
    encoded = _json_line(payload)
    while len(client.out_queue) >= client.queue_limit:
        client.out_queue.popleft()
        client.write_offset = 0
    client.out_queue.append(encoded)


def _close_client(
    selector: selectors.BaseSelector,
    clients: dict[socket.socket, _Client],
    sock: socket.socket,
) -> None:
    try:
        selector.unregister(sock)
    except Exception:
        pass
    client = clients.pop(sock, None)
    try:
        sock.close()
    except Exception:
        pass
    if client is not None:
        client.out_queue.clear()


def _broadcast(
    clients: dict[socket.socket, _Client],
    envelope: dict[str, Any],
) -> None:
    topic = str(envelope.get("topic", ""))
    for client in list(clients.values()):
        if client.subscribed and _topic_matches(topic, client.subscriptions):
            _enqueue(client, {"op": "event", "envelope": envelope})


def _build_envelope(
    topic: str,
    event_type: str,
    *,
    source: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "event_id": f"project-os-{uuid.uuid4().hex[:10]}",
        "topic": topic,
        "event_type": event_type,
        "source": source,
        "timestamp": utc_now(),
        "payload": payload or {},
    }


def publish_project_os_event(
    topic: str,
    event_type: str,
    *,
    source: str,
    payload: dict[str, Any] | None = None,
    timeout_seconds: float = 0.2,
) -> dict[str, Any]:
    envelope = _build_envelope(topic, event_type, source=source, payload=payload)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout_seconds)
    try:
        sock.connect(str(_socket_path()))
        sock.sendall(_json_line({"op": "publish", "envelope": envelope}))
    finally:
        sock.close()
    return envelope


def publish_project_os_event_best_effort(
    topic: str,
    event_type: str,
    *,
    source: str,
    payload: dict[str, Any] | None = None,
    timeout_seconds: float = 0.2,
) -> dict[str, Any] | None:
    try:
        return publish_project_os_event(
            topic,
            event_type,
            source=source,
            payload=payload,
            timeout_seconds=timeout_seconds,
        )
    except Exception:
        return None


def format_project_os_event(envelope: dict[str, Any]) -> str:
    topic = str(envelope.get("topic", ""))
    event_type = str(envelope.get("event_type", ""))
    source = str(envelope.get("source", ""))
    timestamp = str(envelope.get("timestamp", ""))
    payload = (
        envelope.get("payload") if isinstance(envelope.get("payload"), dict) else {}
    )
    summary = ""
    if topic == "authority.audit":
        summary = str(payload.get("event_type", payload.get("reason", "")))
    elif topic == "system.service":
        summary = str(payload.get("service_name", "service"))
    elif topic == "system.authority":
        summary = str(payload.get("summary", payload.get("service_name", "authority")))
    else:
        summary = str(payload.get("summary", payload.get("message", "")))
    suffix = f" :: {summary}" if summary else ""
    return f"[{topic}] {timestamp} {event_type} source={source}{suffix}"


def get_project_os_bus_status(
    *,
    timeout_seconds: float = DEFAULT_BUS_STATUS_TIMEOUT,
) -> dict[str, Any]:
    path = _socket_path()
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(max(0.05, float(timeout_seconds)))
    buffer = bytearray()
    deadline = time.time() + max(0.05, float(timeout_seconds))
    try:
        sock.connect(str(path))
        sock.sendall(_json_line({"op": "status"}))
        while time.time() < deadline:
            try:
                chunk = sock.recv(4096)
            except TimeoutError:
                continue
            if not chunk:
                break
            buffer.extend(chunk)
            while b"\n" in buffer:
                line, _, remainder = buffer.partition(b"\n")
                buffer = bytearray(remainder)
                if not line.strip():
                    continue
                message = json.loads(line.decode("utf-8"))
                if message.get("op") != "status":
                    continue
                broker = message.get("broker")
                if not isinstance(broker, dict):
                    break
                return {
                    "success": True,
                    "socket_path": str(path),
                    "socket_exists": True,
                    "broker_available": True,
                    "connected_clients": int(broker.get("connected_clients", 0) or 0),
                    "subscribed_clients": int(broker.get("subscribed_clients", 0) or 0),
                    "published_events": int(broker.get("published_events", 0) or 0),
                    "uptime_seconds": float(broker.get("uptime_seconds", 0.0) or 0.0),
                    "timestamp": str(message.get("timestamp", "") or ""),
                }
    except OSError as exc:
        return {
            "success": True,
            "socket_path": str(path),
            "socket_exists": path.exists(),
            "broker_available": False,
            "connected_clients": 0,
            "subscribed_clients": 0,
            "published_events": 0,
            "uptime_seconds": 0.0,
            "reason": f"broker unavailable: {exc}",
        }
    finally:
        sock.close()
    return {
        "success": True,
        "socket_path": str(path),
        "socket_exists": path.exists(),
        "broker_available": False,
        "connected_clients": 0,
        "subscribed_clients": 0,
        "published_events": 0,
        "uptime_seconds": 0.0,
        "reason": "broker did not return status response",
    }


def tail_project_os_events(
    *,
    topics: list[str] | None = None,
    seconds: float = DEFAULT_TAIL_SECONDS,
    max_events: int = DEFAULT_TAIL_MAX_EVENTS,
) -> dict[str, Any]:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(DEFAULT_SELECT_TIMEOUT)
    events: list[dict[str, Any]] = []
    buffer = bytearray()
    deadline = time.time() + max(0.1, float(seconds))
    try:
        sock.connect(str(_socket_path()))
        sock.sendall(
            _json_line(
                {
                    "op": "subscribe",
                    "topics": topics or ["system.", "authority."],
                    "queue_limit": DEFAULT_QUEUE_LIMIT,
                }
            )
        )
        while time.time() < deadline and len(events) < max(1, int(max_events)):
            try:
                chunk = sock.recv(4096)
            except TimeoutError:
                continue
            if not chunk:
                break
            buffer.extend(chunk)
            while b"\n" in buffer:
                line, _, remainder = buffer.partition(b"\n")
                buffer = bytearray(remainder)
                if not line.strip():
                    continue
                message = json.loads(line.decode("utf-8"))
                if message.get("op") != "event":
                    continue
                envelope = message.get("envelope")
                if isinstance(envelope, dict):
                    events.append(envelope)
                    if len(events) >= max(1, int(max_events)):
                        break
    except OSError as exc:
        return {
            "success": False,
            "socket_path": str(_socket_path()),
            "count": 0,
            "topics": topics or ["system.", "authority."],
            "reason": f"broker unavailable: {exc}",
            "lines": [],
            "timeline": "",
            "events": [],
        }
    finally:
        sock.close()
    lines = [format_project_os_event(event) for event in events]
    return {
        "success": True,
        "socket_path": str(_socket_path()),
        "count": len(events),
        "topics": topics or ["system.", "authority."],
        "lines": lines,
        "timeline": "\n".join(lines),
        "events": events,
    }


def run_event_broker() -> int:
    path = _socket_path()
    if path.exists():
        path.unlink()

    started_at = time.time()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(path))
    server.listen()
    server.setblocking(False)
    selector = selectors.DefaultSelector()
    selector.register(server, selectors.EVENT_READ)
    clients: dict[socket.socket, _Client] = {}
    sequence = 0

    try:
        while True:
            for key, mask in selector.select(timeout=DEFAULT_SELECT_TIMEOUT):
                if key.fileobj is server:
                    conn, _ = server.accept()
                    conn.setblocking(False)
                    client = _Client(sock=conn)
                    clients[conn] = client
                    selector.register(
                        conn, selectors.EVENT_READ | selectors.EVENT_WRITE
                    )
                    continue

                sock = key.fileobj
                client = clients.get(sock)
                if client is None:
                    continue

                if mask & selectors.EVENT_READ:
                    try:
                        chunk = sock.recv(4096)
                    except BlockingIOError:
                        chunk = b""
                    except Exception:
                        _close_client(selector, clients, sock)
                        continue
                    if chunk == b"":
                        _close_client(selector, clients, sock)
                        continue
                    client.in_buffer.extend(chunk)
                    while b"\n" in client.in_buffer:
                        line, _, remainder = client.in_buffer.partition(b"\n")
                        client.in_buffer = bytearray(remainder)
                        if not line.strip():
                            continue
                        try:
                            message = json.loads(line.decode("utf-8"))
                        except Exception:
                            continue
                        op = str(message.get("op", ""))
                        if op == "subscribe":
                            raw_topics = message.get("topics")
                            client.subscriptions = (
                                [str(item) for item in raw_topics if str(item).strip()]
                                if isinstance(raw_topics, list)
                                else []
                            )
                            client.queue_limit = max(
                                1,
                                int(
                                    message.get("queue_limit", DEFAULT_QUEUE_LIMIT) or 0
                                ),
                            )
                            client.subscribed = True
                            _enqueue(
                                client,
                                {
                                    "op": "subscribed",
                                    "topics": client.subscriptions,
                                    "timestamp": utc_now(),
                                },
                            )
                        elif op == "publish":
                            envelope = message.get("envelope")
                            if not isinstance(envelope, dict):
                                continue
                            sequence += 1
                            broker_envelope = dict(envelope)
                            broker_envelope.setdefault(
                                "event_id", f"project-os-{uuid.uuid4().hex[:10]}"
                            )
                            broker_envelope.setdefault("timestamp", utc_now())
                            broker_envelope["sequence"] = sequence
                            _broadcast(clients, broker_envelope)
                        elif op == "status":
                            _enqueue(
                                client,
                                {
                                    "op": "status",
                                    "timestamp": utc_now(),
                                    "broker": {
                                        "connected_clients": len(clients),
                                        "subscribed_clients": sum(
                                            1
                                            for active_client in clients.values()
                                            if active_client.subscribed
                                        ),
                                        "published_events": sequence,
                                        "uptime_seconds": round(
                                            max(0.0, time.time() - started_at),
                                            3,
                                        ),
                                    },
                                },
                            )

                if mask & selectors.EVENT_WRITE and client.out_queue:
                    payload = client.out_queue[0]
                    try:
                        sent = sock.send(payload[client.write_offset :])
                    except BlockingIOError:
                        sent = 0
                    except Exception:
                        _close_client(selector, clients, sock)
                        continue
                    client.write_offset += sent
                    if client.write_offset >= len(payload):
                        client.out_queue.popleft()
                        client.write_offset = 0
    finally:
        for sock in list(clients):
            _close_client(selector, clients, sock)
        try:
            selector.unregister(server)
        except Exception:
            pass
        server.close()
        path.unlink(missing_ok=True)
    return 0
