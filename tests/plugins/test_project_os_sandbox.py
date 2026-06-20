from __future__ import annotations

import io
import json
import os
import sys
import tarfile
from pathlib import Path

from code_puppy.plugins.project_os_supervisor import __main__ as main_mod
from code_puppy.plugins.project_os_supervisor import manager, sandbox, tooling
from code_puppy.plugins.project_os_supervisor.state import load_manifest


def _write_manifest(tmp_path: Path, services: list[dict]) -> Path:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"manifest_version": "1.0.0", "services": services}, indent=2) + "\n"
    )
    return manifest_path


def _make_rootfs_tarball(tmp_path: Path) -> Path:
    tar_path = tmp_path / "mini-rootfs.tar.gz"
    members = {
        "bin/sh": "#!/bin/sh\nexit 0\n",
        "usr/bin/env": "#!/bin/sh\nexit 0\n",
        "root/.keep": "",
    }
    with tarfile.open(tar_path, "w:gz") as archive:
        for name, content in members.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            info.mode = 0o755 if name.endswith(("/sh", "/env")) else 0o644
            archive.addfile(info, io.BytesIO(data))
    return tar_path


class _DummyProcess:
    def __init__(self, pid: int = 4242):
        self.pid = pid
        self.returncode = None

    def poll(self):
        return None


class TestProjectOsSandbox:
    def test_cli_init_sandbox_extracts_rootfs(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("PROJECT_OS_SANDBOXES_ROOT", str(tmp_path / "sandboxes"))
        tarball = _make_rootfs_tarball(tmp_path)

        monkeypatch.setattr(
            sys,
            "argv",
            [
                "project-os-supervisor",
                "init-sandbox",
                "--sandbox",
                "alpha",
                "--rootfs-tarball",
                str(tarball),
            ],
        )
        try:
            main_mod.main()
        except SystemExit as exc:
            assert exc.code == 0

        output = json.loads(capsys.readouterr().out)
        sandbox_result = output["sandboxes"][0]
        rootfs_path = Path(sandbox_result["rootfs_path"])
        assert output["success"] is True
        assert sandbox_result["sandbox_name"] == "alpha"
        assert (rootfs_path / "bin" / "sh").exists()
        assert (rootfs_path.parent / ".rootfs_initialized.json").exists()

    def test_build_service_launch_spec_wraps_proot_command_and_binds(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("PROJECT_OS_SANDBOXES_ROOT", str(tmp_path / "sandboxes"))
        monkeypatch.setenv("PROJECT_OS_PROOT_BINARY", "/fake/bin/proot")
        socket_dir = tmp_path / "socket-dir"
        socket_dir.mkdir()
        monkeypatch.setenv(
            "PROJECT_OS_EVENT_SOCKET_PATH", str(socket_dir / "project_os_events.sock")
        )

        tarball = _make_rootfs_tarball(tmp_path)
        shared_dir = tmp_path / "shared"
        shared_dir.mkdir()
        manifest_path = _write_manifest(
            tmp_path,
            [
                {
                    "name": "isolated-worker",
                    "runtime": "proot",
                    "sandbox_name": "alpha",
                    "sandbox_rootfs_tarball": str(tarball),
                    "sandbox_bind_mounts": [f"{shared_dir}:/mnt/shared"],
                    "command": ["python3", "worker.py"],
                    "cwd": "work",
                    "autostart": False,
                    "restart_policy": "never",
                }
            ],
        )
        service = load_manifest(manifest_path)[0]
        heartbeat_file = tmp_path / "heartbeats" / "worker.json"
        heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
        heartbeat_file.write_text("{}\n")

        spec = sandbox.build_service_launch_spec(
            manifest_path=manifest_path,
            service=service,
            environment={
                "PROJECT_OS_EVENT_SOCKET_PATH": str(
                    socket_dir / "project_os_events.sock"
                ),
                "PROJECT_OS_HEARTBEAT_PATH": str(heartbeat_file),
                "PROJECT_OS_SERVICE_NAME": service.name,
                "PROJECT_OS_SUPERVISOR_MANIFEST": str(manifest_path),
                "PROJECT_OS_SUPERVISOR_ROOT": str(tmp_path / "supervisor"),
                "PYTHONPATH": os.getcwd(),
            },
            heartbeat_file=heartbeat_file,
        )

        assert spec.runtime == "proot"
        assert spec.command[0] == "/fake/bin/proot"
        assert spec.command[-2:] == ["python3", "worker.py"]
        assert "-r" in spec.command
        assert "-w" in spec.command
        assert spec.sandbox_rootfs_path is not None
        bind_specs = spec.bind_mounts or []
        assert any(str(socket_dir) in item for item in bind_specs)
        assert any(str(heartbeat_file.parent) in item for item in bind_specs)
        assert any(item.endswith(":/mnt/shared") for item in bind_specs)
        assert spec.cwd == str(tmp_path)

    def test_start_manifest_fails_cleanly_without_proot_binary(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("PROJECT_OS_SANDBOXES_ROOT", str(tmp_path / "sandboxes"))
        monkeypatch.delenv("PROJECT_OS_PROOT_BINARY", raising=False)
        monkeypatch.setattr(sandbox, "proot_binary", lambda: None)
        tarball = _make_rootfs_tarball(tmp_path)
        manifest_path = _write_manifest(
            tmp_path,
            [
                {
                    "name": "isolated-worker",
                    "runtime": "proot",
                    "sandbox_name": "alpha",
                    "sandbox_rootfs_tarball": str(tarball),
                    "command": ["python3", "worker.py"],
                    "cwd": ".",
                    "autostart": True,
                    "restart_policy": "never",
                }
            ],
        )

        result = tooling.project_os_supervisor_start_manifest(str(manifest_path))

        assert result["success"] is False
        assert "proot" in result["reason"].lower()
        assert result["started"] == []

    def test_manager_start_child_uses_proot_launch_wrapper(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PROJECT_OS_SANDBOXES_ROOT", str(tmp_path / "sandboxes"))
        monkeypatch.setenv("PROJECT_OS_PROOT_BINARY", "/fake/bin/proot")
        monkeypatch.setenv("PROJECT_OS_SUPERVISOR_ROOT", str(tmp_path / "supervisor"))
        socket_dir = tmp_path / "socket-dir"
        socket_dir.mkdir()
        monkeypatch.setenv(
            "PROJECT_OS_EVENT_SOCKET_PATH", str(socket_dir / "project_os_events.sock")
        )
        tarball = _make_rootfs_tarball(tmp_path)
        manifest_path = _write_manifest(
            tmp_path,
            [
                {
                    "name": "isolated-worker",
                    "runtime": "proot",
                    "sandbox_name": "alpha",
                    "sandbox_rootfs_tarball": str(tarball),
                    "command": ["python3", "worker.py"],
                    "cwd": "work",
                    "autostart": False,
                    "restart_policy": "never",
                }
            ],
        )
        service = load_manifest(manifest_path)[0]
        captured: dict[str, object] = {}

        def fake_popen(command, **kwargs):
            captured["command"] = command
            captured["cwd"] = kwargs.get("cwd")
            captured["env"] = kwargs.get("env")
            return _DummyProcess()

        monkeypatch.setattr(manager.subprocess, "Popen", fake_popen)

        process, launch_spec = manager._start_child(manifest_path, service)

        assert process.pid == 4242
        assert launch_spec.runtime == "proot"
        assert captured["command"][0] == "/fake/bin/proot"
        assert captured["cwd"] == str(tmp_path)
        assert captured["env"]["PROJECT_OS_EVENT_SOCKET_PATH"].endswith(
            "project_os_events.sock"
        )
        assert captured["env"]["PROJECT_OS_SANDBOX_NAME"] == "alpha"
