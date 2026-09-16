from __future__ import annotations

from code_puppy import bootstrap, bootstrap_profiles, bootstrap_wizard


def _fake_env(**overrides):
    base = {
        "python_executable": "/usr/bin/python3",
        "python_version": "3.13.13",
        "platform_system": "Linux",
        "platform_release": "android",
        "platform_machine": "aarch64",
        "has_uv": True,
        "has_uvx": True,
        "has_proot": True,
        "has_ripgrep": True,
        "has_rust": True,
        "has_clang": True,
        "has_git": True,
        "is_android": False,
        "is_termux": False,
        "is_linux": True,
        "is_macos": False,
        "is_windows": False,
    }
    base.update(overrides)
    return base


def _patch_env(monkeypatch, **overrides):
    monkeypatch.setattr(
        bootstrap_profiles,
        "detect_environment",
        lambda: _fake_env(**overrides),
    )


def test_bare_termux_device_builds_three_steps(monkeypatch):
    _patch_env(
        monkeypatch,
        is_android=True,
        is_termux=True,
        has_uv=False,
        has_proot=False,
        has_ripgrep=False,
        has_rust=False,
        has_clang=False,
    )
    steps, plan = bootstrap_wizard.build_steps(profile="auto")
    keys = [step.key for step in steps]
    assert keys == ["uv", "system_packages", "code_puppy"]

    by_key = {step.key: step for step in steps}
    assert by_key["uv"].command == "pip install uv"
    assert (
        by_key["system_packages"].command == "pkg install -y rust clang ripgrep proot"
    )
    assert plan["profile"] == "android-termux-lean"


def test_loaded_device_collapses_to_single_step(monkeypatch):
    _patch_env(monkeypatch, is_android=True, is_termux=True)
    steps, _ = bootstrap_wizard.build_steps(profile="auto")
    assert [step.key for step in steps] == ["code_puppy"]


def test_desktop_missing_uv_uses_curl_installer(monkeypatch):
    _patch_env(monkeypatch, has_uv=False)
    steps, _ = bootstrap_wizard.build_steps(profile="core")
    uv_step = next(step for step in steps if step.key == "uv")
    assert "astral.sh/uv/install.sh" in uv_step.command


def test_dry_run_executes_nothing(monkeypatch, capsys):
    _patch_env(monkeypatch, is_android=True, is_termux=True)

    def _boom(_command):
        raise AssertionError("dry-run must not execute commands")

    monkeypatch.setattr(bootstrap_wizard, "_run_command", _boom)
    code = bootstrap_wizard.run_wizard(profile="auto", dry_run=True)
    out = capsys.readouterr().out
    assert code == 0
    assert "DRY-RUN" in out
    assert "dry-run, not executed" in out


def test_yes_runs_steps_and_verifies(monkeypatch, capsys):
    _patch_env(
        monkeypatch,
        is_android=True,
        is_termux=True,
        has_ripgrep=False,
        has_proot=False,
        has_rust=False,
        has_clang=False,
    )

    calls = []

    def _fake_run(command):
        calls.append(command)
        return 0, "ok"

    monkeypatch.setattr(bootstrap_wizard, "_run_command", _fake_run)
    monkeypatch.setattr(bootstrap_wizard, "_has", lambda binary: binary == "code-puppy")

    code = bootstrap_wizard.run_wizard(profile="auto", assume_yes=True)
    out = capsys.readouterr().out
    assert code == 0
    assert any("pkg install -y rust clang ripgrep proot" in call for call in calls)
    assert any("uv tool install" in call for call in calls)
    assert "Verification: OK" in out


def test_required_failure_stops_and_returns_one(monkeypatch, capsys):
    _patch_env(
        monkeypatch,
        is_android=True,
        is_termux=True,
        has_ripgrep=False,
        has_proot=False,
        has_rust=False,
        has_clang=False,
    )

    def _fail(_command):
        return 1, "pkg: network unreachable"

    monkeypatch.setattr(bootstrap_wizard, "_run_command", _fail)
    code = bootstrap_wizard.run_wizard(profile="auto", assume_yes=True)
    out = capsys.readouterr().out
    assert code == 1
    assert "FAILED" in out
    assert "stopping" in out.lower()


def test_verify_fails_when_binary_absent(monkeypatch):
    _patch_env(monkeypatch)
    monkeypatch.setattr(bootstrap_wizard, "_has", lambda _binary: False)
    outcome = bootstrap_wizard._verify({})
    assert outcome.status == "failed"


def test_cli_wizard_dry_run_via_main(capsys):
    exit_code = bootstrap.main(["wizard", "--dry-run"])
    assert exit_code == 0
    assert "install wizard" in capsys.readouterr().out.lower()
