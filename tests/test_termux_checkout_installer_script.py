from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install_termux_checkout.sh"


def test_termux_checkout_installer_shell_syntax_is_valid():
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_termux_checkout_installer_dry_run_supports_repo_and_ref():
    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--dry-run",
            "--yes",
            "--skip-upgrade",
            "--repo-url",
            "https://github.com/example/code_puppy.git",
            "--ref",
            "feature/android-fix",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "repo    : https://github.com/example/code_puppy.git" in result.stdout
    assert "ref     : feature/android-fix" in result.stdout
    assert "+ git clone https://github.com/example/code_puppy.git" in result.stdout
    assert (
        "git -C \\$HOME/code-puppy-checkout-preview checkout feature/android-fix"
        in result.stdout
    )
    assert (
        "+ cd \\$HOME/code-puppy-checkout-preview && uv sync --no-dev --python python"
        in result.stdout
    )
    assert (
        "+ cd \\$HOME/code-puppy-checkout-preview && uv run --no-dev --python python code-puppy --help"
        in result.stdout
    )
    assert (
        "+ cd \\$HOME/code-puppy-checkout-preview && uv run --no-dev --python python code-puppy-bootstrap plan --profile auto"
        in result.stdout
    )
    assert "code-puppy -i" not in result.stdout


def test_termux_checkout_installer_help_mentions_source_checkout_contract():
    result = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "source-checkout installer/validator" in result.stdout
    assert "--repo-url <url>" in result.stdout
    assert "--ref <ref>" in result.stdout
    assert "--require-clean" in result.stdout
