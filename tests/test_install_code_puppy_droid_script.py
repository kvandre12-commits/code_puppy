from pathlib import Path


SCRIPT_PATH = Path("scripts/install-code-puppy-droid.sh")


def _script_text() -> str:
    return SCRIPT_PATH.read_text(encoding="utf-8")


def test_droid_install_script_bootstraps_with_uv_and_termux_basics():
    script = _script_text()

    assert "pkg install -y python git android-tools termux-api ripgrep proot" in script
    assert "pkg install -y uv" in script
    assert 'uv tool install --refresh "$PACKAGE_SPEC"' in script


def test_droid_install_script_points_users_at_bootstrap_commands_not_repo_docs():
    script = _script_text()

    assert "code-puppy-bootstrap wizard" in script
    assert "code-puppy-bootstrap detect --json" in script
    assert "docs/ANDROID.md" not in script
