from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install_termux.sh"


def test_termux_installer_shell_syntax_is_valid():
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_termux_installer_dry_run_supports_version_pin():
    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--dry-run",
            "--yes",
            "--no-launch",
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
    assert "package : code-puppy==9.9.9" in result.stdout
    assert (
        "+ uvx --from code-puppy==9.9.9 code-puppy-bootstrap detect --json"
        in result.stdout
    )
    assert "+ uv tool install --refresh code-puppy==9.9.9" in result.stdout
    assert "+ code-puppy --help" in result.stdout
    assert "+ code-puppy -i" not in result.stdout


def test_termux_installer_help_mentions_clean_run_support():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "--require-clean" in result.stdout
    assert "--version <ver>" in result.stdout
