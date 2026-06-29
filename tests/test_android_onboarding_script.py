from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "onboard_android.sh"


def test_android_onboarding_shell_syntax_is_valid():
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_android_onboarding_help_mentions_milestone_flags():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "--skip-overlay" in result.stdout
    assert "--skip-adb-install" in result.stdout
    assert "--launch" in result.stdout


def test_android_onboarding_dry_run_prints_staged_summary():
    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--dry-run",
            "--yes",
            "--skip-upgrade",
            "--version",
            "9.9.9",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "Android onboarding command" in result.stdout
    assert "+ bash" in result.stdout
    assert (
        "install_termux.sh --no-launch --version 9.9.9 --yes --dry-run --skip-upgrade"
        in result.stdout
    )
    assert "install_overlay.py --overwrite --dry-run" in result.stdout
    assert "Android Onboarding Summary" in result.stdout
    assert "Core Code Puppy:" in result.stdout
    assert "ADB / Wireless Debugging:" in result.stdout
    assert "+ code-puppy -i" not in result.stdout
