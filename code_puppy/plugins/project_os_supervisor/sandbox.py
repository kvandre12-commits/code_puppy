from __future__ import annotations

import json
import os
import platform
import shutil
import tarfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .state import ServiceManifest, event_socket_path

DEFAULT_SANDBOX_NAME = "default"
DEFAULT_GUEST_HOME = "/root"
DEFAULT_GUEST_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
DEFAULT_ALPINE_VERSION = "3.20.5"
DEFAULT_SANDBOXES_ROOT = Path.home() / ".project_os" / "sandboxes"

_ARCH_TO_ALPINE = {
    "aarch64": "aarch64",
    "arm64": "aarch64",
    "armv7l": "armv7",
    "armv8l": "armv7",
    "x86_64": "x86_64",
    "amd64": "x86_64",
    "i686": "x86",
    "i386": "x86",
}


@dataclass(frozen=True)
class LaunchSpec:
    command: list[str]
    cwd: str
    runtime: str
    sandbox_rootfs_path: str | None = None
    bind_mounts: list[str] | None = None


def get_sandboxes_root() -> Path:
    raw = os.environ.get("PROJECT_OS_SANDBOXES_ROOT", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return DEFAULT_SANDBOXES_ROOT


def sandbox_dir(sandbox_name: str = DEFAULT_SANDBOX_NAME) -> Path:
    return get_sandboxes_root() / sandbox_name


def sandbox_rootfs_path(sandbox_name: str = DEFAULT_SANDBOX_NAME) -> Path:
    return sandbox_dir(sandbox_name) / "rootfs"


def sandbox_cache_dir(sandbox_name: str = DEFAULT_SANDBOX_NAME) -> Path:
    return sandbox_dir(sandbox_name) / "cache"


def sandbox_marker_path(sandbox_name: str = DEFAULT_SANDBOX_NAME) -> Path:
    return sandbox_dir(sandbox_name) / ".rootfs_initialized.json"


def proot_binary() -> str | None:
    explicit = os.environ.get("PROJECT_OS_PROOT_BINARY", "").strip()
    if explicit:
        return explicit
    return shutil.which("proot")


def _default_alpine_arch() -> str:
    raw = (os.environ.get("PROJECT_OS_SANDBOX_ARCH") or platform.machine()).lower()
    return _ARCH_TO_ALPINE.get(raw, raw)


def default_rootfs_url() -> str:
    override = os.environ.get("PROJECT_OS_SANDBOX_ROOTFS_URL", "").strip()
    if override:
        return override
    arch = _default_alpine_arch()
    filename = f"alpine-minirootfs-{DEFAULT_ALPINE_VERSION}-{arch}.tar.gz"
    return f"https://dl-cdn.alpinelinux.org/alpine/v3.20/releases/{arch}/{filename}"


def _rootfs_is_initialized(rootfs_path: Path) -> bool:
    markers = [
        rootfs_path / "bin" / "sh",
        rootfs_path / "usr" / "bin" / "env",
        rootfs_path / "bin" / "busybox",
    ]
    return any(path.exists() or path.is_symlink() for path in markers)


def _resolve_tarball_path(source: str, *, manifest_path: Path | None = None) -> Path:
    candidate = Path(source).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    if manifest_path is not None:
        return (manifest_path.parent / candidate).resolve()
    return candidate.resolve()


def _download_rootfs_archive(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    return destination


def _safe_extract(tar_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, mode="r:*") as archive:
        destination_resolved = destination.resolve()
        for member in archive.getmembers():
            member_path = (destination / member.name).resolve()
            if (
                destination_resolved not in member_path.parents
                and member_path != destination_resolved
            ):
                raise ValueError(f"unsafe archive member: {member.name}")
        try:
            archive.extractall(destination, filter="data")
        except (TypeError, tarfile.TarError):
            archive.extractall(destination)


def initialize_sandbox_rootfs(
    sandbox_name: str = DEFAULT_SANDBOX_NAME,
    *,
    manifest_path: str | Path | None = None,
    rootfs_tarball: str = "",
    rootfs_url: str = "",
) -> dict[str, Any]:
    sandbox_name = sandbox_name.strip() or DEFAULT_SANDBOX_NAME
    rootfs_path = sandbox_rootfs_path(sandbox_name)
    cache_dir = sandbox_cache_dir(sandbox_name)
    marker_path = sandbox_marker_path(sandbox_name)
    cache_dir.mkdir(parents=True, exist_ok=True)
    rootfs_path.mkdir(parents=True, exist_ok=True)

    if _rootfs_is_initialized(rootfs_path):
        return {
            "success": True,
            "sandbox_name": sandbox_name,
            "rootfs_path": str(rootfs_path),
            "initialized": False,
            "already_present": True,
            "marker_path": str(marker_path),
        }

    manifest = Path(manifest_path).expanduser().resolve() if manifest_path else None
    archive_path: Path
    source_ref: str
    downloaded = False

    if rootfs_tarball.strip():
        archive_path = _resolve_tarball_path(
            rootfs_tarball.strip(), manifest_path=manifest
        )
        if not archive_path.exists():
            raise FileNotFoundError(f"rootfs tarball not found: {archive_path}")
        source_ref = str(archive_path)
    else:
        source_url = rootfs_url.strip() or default_rootfs_url()
        parsed = urllib.parse.urlparse(source_url)
        filename = Path(parsed.path).name or "sandbox-rootfs.tar.gz"
        archive_path = cache_dir / filename
        if not archive_path.exists():
            _download_rootfs_archive(source_url, archive_path)
            downloaded = True
        source_ref = source_url

    _safe_extract(archive_path, rootfs_path)
    if not _rootfs_is_initialized(rootfs_path):
        raise RuntimeError(
            f"sandbox rootfs did not look valid after extraction: {rootfs_path}"
        )

    marker_payload = {
        "sandbox_name": sandbox_name,
        "rootfs_path": str(rootfs_path),
        "source": source_ref,
        "downloaded": downloaded,
    }
    marker_path.write_text(json.dumps(marker_payload, indent=2, sort_keys=True) + "\n")
    return {
        "success": True,
        "sandbox_name": sandbox_name,
        "rootfs_path": str(rootfs_path),
        "initialized": True,
        "already_present": False,
        "downloaded": downloaded,
        "source": source_ref,
        "archive_path": str(archive_path),
        "marker_path": str(marker_path),
    }


def _guest_cwd(raw_cwd: str) -> str:
    value = (raw_cwd or "").strip()
    if not value or value == ".":
        return DEFAULT_GUEST_HOME
    if value.startswith("/"):
        return value
    return f"{DEFAULT_GUEST_HOME}/{value}"


def _parse_bind_mount(spec: str, *, manifest_path: Path) -> tuple[Path, str]:
    raw = spec.strip()
    if not raw:
        raise ValueError("sandbox bind mount entries cannot be empty")
    if ":" in raw:
        host_raw, guest_raw = raw.split(":", 1)
    else:
        host_raw, guest_raw = raw, raw
    host_path = _resolve_tarball_path(host_raw, manifest_path=manifest_path)
    if not host_path.exists():
        raise FileNotFoundError(f"sandbox bind host path not found: {host_path}")
    guest_path = guest_raw.strip() or str(host_path)
    if not guest_path.startswith("/"):
        raise ValueError(f"sandbox guest bind target must be absolute: {guest_path}")
    return host_path, guest_path


def _ensure_guest_target(rootfs_path: Path, guest_path: str, *, is_dir: bool) -> None:
    target = rootfs_path / guest_path.lstrip("/")
    if is_dir:
        target.mkdir(parents=True, exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch(exist_ok=True)


def _default_bind_mounts(heartbeat_file: Path) -> list[tuple[Path, str]]:
    socket_dir = event_socket_path().parent.resolve()
    return [
        (socket_dir, str(socket_dir)),
        (heartbeat_file.parent.resolve(), str(heartbeat_file.parent.resolve())),
    ]


def _sandbox_child_env(
    environment: dict[str, str], service: ServiceManifest
) -> list[str]:
    keys = set(service.env)
    keys.update(
        {
            "HOME",
            "LANG",
            "LC_ALL",
            "PATH",
            "PROJECT_OS_EVENT_SOCKET_PATH",
            "PROJECT_OS_HEARTBEAT_INTERVAL_SECONDS",
            "PROJECT_OS_HEARTBEAT_PATH",
            "PROJECT_OS_SANDBOX_NAME",
            "PROJECT_OS_SERVICE_NAME",
            "PROJECT_OS_SUPERVISOR_MANIFEST",
            "PROJECT_OS_SUPERVISOR_ROOT",
            "PYTHONPATH",
            "TERM",
            "TMPDIR",
        }
    )
    assignments = {
        "HOME": DEFAULT_GUEST_HOME,
        "PATH": DEFAULT_GUEST_PATH,
    }
    for key, value in environment.items():
        if key in keys or key.startswith("PROJECT_OS_") or key.startswith("PYTHON"):
            assignments[key] = value
    return [f"{key}={assignments[key]}" for key in sorted(assignments)]


def preflight_service_runtime(
    manifest_path: str | Path,
    service: ServiceManifest,
) -> dict[str, Any]:
    if service.runtime != "proot":
        return {"success": True, "runtime": service.runtime}
    binary = proot_binary()
    if not binary:
        raise RuntimeError(
            "runtime=proot requested but `proot` was not found. Install it or set PROJECT_OS_PROOT_BINARY."
        )
    result = initialize_sandbox_rootfs(
        service.sandbox_name,
        manifest_path=manifest_path,
        rootfs_tarball=service.sandbox_rootfs_tarball,
        rootfs_url=service.sandbox_rootfs_url,
    )
    return {
        "success": True,
        "runtime": service.runtime,
        "sandbox_name": service.sandbox_name,
        "rootfs_path": result["rootfs_path"],
        "proot_binary": binary,
    }


def build_service_launch_spec(
    manifest_path: str | Path,
    service: ServiceManifest,
    environment: dict[str, str],
    heartbeat_file: Path,
) -> LaunchSpec:
    manifest = Path(manifest_path).expanduser().resolve()
    if service.runtime != "proot":
        return LaunchSpec(
            command=service.command,
            cwd=str(Path(service.cwd).expanduser().resolve()),
            runtime=service.runtime,
        )

    runtime_info = preflight_service_runtime(manifest, service)
    rootfs = Path(str(runtime_info["rootfs_path"]))
    guest_cwd = _guest_cwd(service.cwd)
    bind_mounts = _default_bind_mounts(heartbeat_file)
    bind_mounts.extend(
        _parse_bind_mount(spec, manifest_path=manifest)
        for spec in service.sandbox_bind_mounts
    )

    normalized_binds: list[tuple[Path, str]] = []
    seen: set[tuple[str, str]] = set()
    for host_path, guest_path in bind_mounts:
        key = (str(host_path.resolve()), guest_path)
        if key in seen:
            continue
        seen.add(key)
        normalized_binds.append((host_path.resolve(), guest_path))
        _ensure_guest_target(rootfs, guest_path, is_dir=host_path.is_dir())

    _ensure_guest_target(rootfs, guest_cwd, is_dir=True)
    bind_args: list[str] = []
    bind_specs: list[str] = []
    for host_path, guest_path in normalized_binds:
        spec = f"{host_path}:{guest_path}"
        bind_args.extend(["-b", spec])
        bind_specs.append(spec)

    env_assignments = _sandbox_child_env(environment, service)
    command = [
        runtime_info["proot_binary"],
        "-0",
        "-r",
        str(rootfs),
        "-w",
        guest_cwd,
        *bind_args,
        "/usr/bin/env",
        "-i",
        *env_assignments,
        *service.command,
    ]
    return LaunchSpec(
        command=command,
        cwd=str(manifest.parent),
        runtime=service.runtime,
        sandbox_rootfs_path=str(rootfs),
        bind_mounts=bind_specs,
    )
