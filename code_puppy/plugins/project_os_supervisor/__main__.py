from __future__ import annotations

import argparse
import json

from .bus import run_event_broker, tail_project_os_events
from .manager import (
    run_authority_daemon,
    run_monitor,
    start_manifest,
    stop_manifest,
    stop_service,
    supervisor_status,
    write_authority_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Project OS lightweight supervisor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    write_manifest = subparsers.add_parser("write-authority-manifest")
    write_manifest.add_argument(
        "--output", default="outputs/project_os_authority_manifest.json"
    )

    start = subparsers.add_parser("start")
    start.add_argument("--manifest", required=True)
    start.add_argument("--service", default="")

    stop = subparsers.add_parser("stop")
    stop.add_argument("--manifest", required=True)
    stop.add_argument("--service", required=True)

    stop_all = subparsers.add_parser("stop-manifest")
    stop_all.add_argument("--manifest", required=True)

    status = subparsers.add_parser("status")
    status.add_argument("--manifest", default="")
    status.add_argument("--service", default="")

    monitor = subparsers.add_parser("run-monitor")
    monitor.add_argument("--manifest", required=True)
    monitor.add_argument("--service", required=True)

    authority = subparsers.add_parser("run-authority-daemon")
    authority.add_argument("--max-beats", type=int)

    subparsers.add_parser("run-broker")

    tail = subparsers.add_parser("tail")
    tail.add_argument("--seconds", type=float, default=3.0)
    tail.add_argument("--max-events", type=int, default=20)
    tail.add_argument("--topic", dest="topics", action="append")

    args = parser.parse_args()

    if args.command == "write-authority-manifest":
        result = write_authority_manifest(args.output)
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(0)
    if args.command == "start":
        result = start_manifest(args.manifest, service_name=args.service)
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(0 if result.get("success") else 1)
    if args.command == "stop":
        result = stop_service(args.manifest, args.service)
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(0 if result.get("success") else 1)
    if args.command == "stop-manifest":
        result = stop_manifest(args.manifest)
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(0 if result.get("success") else 1)
    if args.command == "status":
        result = supervisor_status(
            manifest_path=args.manifest or None,
            service_name=args.service,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(0 if result.get("success") else 1)
    if args.command == "run-monitor":
        raise SystemExit(run_monitor(args.manifest, args.service))
    if args.command == "run-authority-daemon":
        raise SystemExit(run_authority_daemon(max_beats=args.max_beats))
    if args.command == "run-broker":
        raise SystemExit(run_event_broker())
    if args.command == "tail":
        result = tail_project_os_events(
            topics=args.topics,
            seconds=args.seconds,
            max_events=args.max_events,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(0 if result.get("success") else 1)

    raise SystemExit(2)


if __name__ == "__main__":
    main()
