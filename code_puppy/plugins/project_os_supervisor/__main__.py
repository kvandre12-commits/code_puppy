from __future__ import annotations

import argparse
import json

from .bus import get_project_os_bus_status, run_event_broker, tail_project_os_events
from .inspection import inspect_manifest
from .manager import (
    initialize_sandbox,
    run_authority_daemon,
    run_monitor,
    start_manifest,
    stop_manifest,
    stop_service,
    supervisor_status,
    write_authority_manifest,
)
from .templates import (
    operator_snapshot,
    start_isolated_job,
    write_isolated_job_manifest,
)


def _parse_env_assignments(values: list[str] | None) -> dict[str, str]:
    assignments: dict[str, str] = {}
    for item in values or []:
        if "=" not in item:
            raise SystemExit(f"Invalid --env value: {item!r}; expected KEY=VALUE")
        key, value = item.split("=", 1)
        clean_key = key.strip()
        if not clean_key:
            raise SystemExit(f"Invalid --env value: {item!r}; key cannot be empty")
        assignments[clean_key] = value
    return assignments


def main() -> None:
    parser = argparse.ArgumentParser(description="Project OS lightweight supervisor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    write_manifest = subparsers.add_parser("write-authority-manifest")
    write_manifest.add_argument(
        "--output", default="outputs/project_os_authority_manifest.json"
    )

    write_job_manifest = subparsers.add_parser("write-isolated-job-manifest")
    write_job_manifest.add_argument(
        "--output", default="outputs/project_os_isolated_job_manifest.json"
    )
    write_job_manifest.add_argument("--service", default="isolated-job")
    write_job_manifest.add_argument(
        "--command", dest="job_command", nargs="+", required=True
    )
    write_job_manifest.add_argument(
        "--runtime",
        choices=["host", "direct", "proot"],
        default="proot",
    )
    write_job_manifest.add_argument("--sandbox", default="isolated-job")
    write_job_manifest.add_argument("--rootfs-tarball", default="")
    write_job_manifest.add_argument("--rootfs-url", default="")
    write_job_manifest.add_argument("--bind", dest="bind_mounts", action="append")
    write_job_manifest.add_argument("--cwd", default="")
    write_job_manifest.add_argument("--env", action="append")
    write_job_manifest.add_argument("--principal-id", default="")
    write_job_manifest.add_argument("--without-authority", action="store_true")
    write_job_manifest.add_argument("--autostart", action="store_true")

    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("--manifest", required=True)

    init_sandbox = subparsers.add_parser("init-sandbox")
    init_sandbox.add_argument("--manifest", default="")
    init_sandbox.add_argument("--service", default="")
    init_sandbox.add_argument("--sandbox", default="default")
    init_sandbox.add_argument("--rootfs-tarball", default="")
    init_sandbox.add_argument("--rootfs-url", default="")

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

    start_isolated = subparsers.add_parser("start-isolated-job")
    start_isolated.add_argument("--manifest", required=True)
    start_isolated.add_argument("--service", default="")
    start_isolated.add_argument("--tail-seconds", type=float, default=0.5)
    start_isolated.add_argument("--max-events", type=int, default=10)
    start_isolated.add_argument("--topic", dest="topics", action="append")

    snapshot = subparsers.add_parser("operator-snapshot")
    snapshot.add_argument("--manifest", required=True)
    snapshot.add_argument("--service", default="")
    snapshot.add_argument("--seconds", type=float, default=0.5)
    snapshot.add_argument("--max-events", type=int, default=10)
    snapshot.add_argument("--topic", dest="topics", action="append")

    monitor = subparsers.add_parser("run-monitor")
    monitor.add_argument("--manifest", required=True)
    monitor.add_argument("--service", required=True)

    authority = subparsers.add_parser("run-authority-daemon")
    authority.add_argument("--max-beats", type=int)

    subparsers.add_parser("run-broker")

    bus_status = subparsers.add_parser("bus-status")
    bus_status.add_argument("--timeout-seconds", type=float, default=0.5)

    tail = subparsers.add_parser("tail")
    tail.add_argument("--seconds", type=float, default=3.0)
    tail.add_argument("--max-events", type=int, default=20)
    tail.add_argument("--topic", dest="topics", action="append")

    args = parser.parse_args()

    if args.command == "write-authority-manifest":
        result = write_authority_manifest(args.output)
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(0)
    if args.command == "write-isolated-job-manifest":
        result = write_isolated_job_manifest(
            output_path=args.output,
            service_name=args.service,
            command=args.job_command,
            runtime=args.runtime,
            sandbox_name=args.sandbox,
            sandbox_rootfs_tarball=args.rootfs_tarball,
            sandbox_rootfs_url=args.rootfs_url,
            sandbox_bind_mounts=args.bind_mounts,
            cwd=args.cwd,
            env=_parse_env_assignments(args.env),
            principal_id=args.principal_id,
            include_authority=not args.without_authority,
            autostart=args.autostart,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(0 if result.get("success") else 1)
    if args.command == "inspect":
        result = inspect_manifest(args.manifest)
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(0 if result.get("valid") else 1)
    if args.command == "init-sandbox":
        result = initialize_sandbox(
            manifest_path=args.manifest or None,
            service_name=args.service,
            sandbox_name=args.sandbox,
            rootfs_tarball=args.rootfs_tarball,
            rootfs_url=args.rootfs_url,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(0 if result.get("success") else 1)
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
    if args.command == "start-isolated-job":
        result = start_isolated_job(
            manifest_path=args.manifest,
            service_name=args.service,
            tail_topics=args.topics,
            tail_seconds=args.tail_seconds,
            tail_max_events=args.max_events,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(0 if result.get("success") else 1)
    if args.command == "operator-snapshot":
        result = operator_snapshot(
            manifest_path=args.manifest,
            service_name=args.service,
            topics=args.topics,
            seconds=args.seconds,
            max_events=args.max_events,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(0 if result.get("success") else 1)
    if args.command == "run-monitor":
        raise SystemExit(run_monitor(args.manifest, args.service))
    if args.command == "run-authority-daemon":
        raise SystemExit(run_authority_daemon(max_beats=args.max_beats))
    if args.command == "run-broker":
        raise SystemExit(run_event_broker())
    if args.command == "bus-status":
        result = get_project_os_bus_status(timeout_seconds=args.timeout_seconds)
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(0 if result.get("broker_available") else 1)
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
