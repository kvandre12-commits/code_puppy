from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "make_android_handoff_packet.py"


def test_android_handoff_packet_help_mentions_lanes_and_output() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "checkout-ref" in result.stdout
    assert "published-artifact" in result.stdout
    assert "--output" in result.stdout


def test_android_handoff_packet_checkout_lane_renders_copy_paste_command() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--lane",
            "checkout-ref",
            "--repo-url",
            "https://github.com/example/code_puppy.git",
            "--ref",
            "feature/android-demo",
            "--no-overlay",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "Android handoff lane: checkout-ref" in result.stdout
    assert "Repo/package target: https://github.com/example/code_puppy.git" in result.stdout
    assert "Git ref: feature/android-demo" in result.stdout
    assert (
        "https://raw.githubusercontent.com/example/code_puppy/feature/android-demo/"
        "scripts/install_termux_checkout.sh"
    ) in result.stdout
    assert "--require-clean" in result.stdout
    assert "Optional overlay attach: not requested." in result.stdout


def test_android_handoff_packet_published_lane_can_write_file(tmp_path: Path) -> None:
    output_path = tmp_path / "packet.md"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--lane",
            "published-artifact",
            "--repo-url",
            "https://github.com/example/code_puppy.git",
            "--ref",
            "release-branch",
            "--published-version",
            "1.2.3",
            "--output",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert f"wrote {output_path}" in result.stdout
    packet = output_path.read_text(encoding="utf-8")
    assert "Android handoff lane: published-artifact" in packet
    assert "Package/version target: code-puppy 1.2.3" in packet
    assert (
        "https://raw.githubusercontent.com/example/code_puppy/release-branch/"
        "scripts/onboard_android.sh"
    ) in packet
    assert "git clone https://github.com/kvandre12-commits/DroidPuppy" in packet
