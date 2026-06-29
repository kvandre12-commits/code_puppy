from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_wheel_metadata.py"


def _run(*command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def test_built_wheel_metadata_keeps_optional_dependencies_optional(tmp_path: Path):
    dist_dir = tmp_path / "dist"
    build_result = _run(
        sys.executable,
        "-m",
        "build",
        "--wheel",
        "--outdir",
        str(dist_dir),
        cwd=ROOT,
    )
    assert build_result.returncode == 0, build_result.stderr or build_result.stdout

    wheels = sorted(dist_dir.glob("code_puppy-*.whl"))
    assert len(wheels) == 1

    check_result = _run(
        sys.executable,
        str(CHECKER),
        "--pyproject",
        "pyproject.toml",
        str(wheels[0]),
        cwd=ROOT,
    )
    assert check_result.returncode == 0, check_result.stdout or check_result.stderr
    assert "metadata-ok:" in check_result.stdout


def test_metadata_checker_rejects_forbidden_optional_dependency_in_base(tmp_path: Path):
    wheel_path = tmp_path / "bad_metadata-0.0.0-py3-none-any.whl"
    metadata = """Metadata-Version: 2.3
Name: bad-metadata
Version: 0.0.0
Requires-Dist: httpx[http2]>=0.24.1
Requires-Dist: mcp>=1.9.4
Requires-Dist: playwright>=1.40.0; extra == 'browser'
"""

    with zipfile.ZipFile(wheel_path, "w") as zf:
        zf.writestr("bad_metadata-0.0.0.dist-info/METADATA", metadata)

    check_result = _run(
        sys.executable,
        str(CHECKER),
        "--pyproject",
        "pyproject.toml",
        str(wheel_path),
        cwd=ROOT,
    )
    assert check_result.returncode == 1
    assert "Forbidden optional-heavy deps leaked into base" in check_result.stdout
    assert "mcp" in check_result.stdout
