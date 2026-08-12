#!/usr/bin/env python3
"""Generate a shareable Android onboarding packet for a repo/ref."""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FALLBACK_INSTALLER_BASE = (
    "https://raw.githubusercontent.com/mpfaffenberger/code_puppy/main/scripts"
)
DEFAULT_OVERLAY_REPO_URL = "https://github.com/kvandre12-commits/DroidPuppy"
REMOTE_CANDIDATES = (("fork", "--push"), ("fork",), ("origin", "--push"), ("origin",))


@dataclass(frozen=True)
class RepoSnapshot:
    repo_url: str
    ref: str
    dirty_count: int


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _discover_repo_url() -> str:
    for candidate in REMOTE_CANDIDATES:
        value = _run_git("remote", "get-url", *candidate)
        if value and not value.startswith("DISABLED-"):
            return value
    return "https://github.com/example/code_puppy.git"


def _discover_ref() -> str:
    branch = _run_git("branch", "--show-current")
    if branch:
        return branch
    commit = _run_git("rev-parse", "--short", "HEAD")
    return commit or "main"


def _dirty_count() -> int:
    status = _run_git("status", "--porcelain")
    if not status:
        return 0
    return len([line for line in status.splitlines() if line.strip()])


def _snapshot(args: argparse.Namespace) -> RepoSnapshot:
    return RepoSnapshot(
        repo_url=args.repo_url or _discover_repo_url(),
        ref=args.ref or _discover_ref(),
        dirty_count=_dirty_count(),
    )


def _github_slug(repo_url: str) -> tuple[str, str] | None:
    https_match = re.match(
        r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", repo_url
    )
    if https_match:
        return https_match.group(1), https_match.group(2)
    ssh_match = re.match(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", repo_url)
    if ssh_match:
        return ssh_match.group(1), ssh_match.group(2)
    return None


def _script_url(repo_url: str, ref: str, script_name: str) -> str:
    slug = _github_slug(repo_url)
    if not slug:
        return f"{FALLBACK_INSTALLER_BASE}/{script_name}"
    owner, repo = slug
    return (
        f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/scripts/{script_name}"
    )


def _published_version(args: argparse.Namespace) -> str:
    if args.published_version:
        return args.published_version
    version_match = re.search(
        r'^version\s*=\s*"([^"]+)"',
        (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    if version_match:
        return version_match.group(1)
    return "<pypi-version>"


def _overlay_section(include_overlay: bool, overlay_repo_url: str) -> str:
    if not include_overlay:
        return "Optional overlay attach: not requested.\n"
    return (
        "Optional DroidPuppy overlay attach:\n\n"
        "```bash\n"
        f"git clone {overlay_repo_url}\n"
        "cd DroidPuppy\n"
        "python scripts/install_overlay.py --overwrite\n"
        "```\n"
    )


def _dirty_note(dirty_count: int) -> str:
    if dirty_count == 0:
        return "Working tree status: clean. Nice. Miraculous, even.\n"
    return (
        f"Working tree status: dirty ({dirty_count} changed paths). "
        "Push or commit the actual branch state before treating this packet as exact proof.\n"
    )


def _checkout_packet(snapshot: RepoSnapshot, args: argparse.Namespace) -> str:
    installer_url = _script_url(
        snapshot.repo_url, snapshot.ref, "install_termux_checkout.sh"
    )
    command = (
        f"curl -fsSL {installer_url} | \\\n"
        f"  bash -s -- --yes --repo-url {snapshot.repo_url} --ref {snapshot.ref} --require-clean"
    )
    return f"""# Android Handoff Packet

Generated: {datetime.now(timezone.utc).isoformat()}
Android handoff lane: checkout-ref
Repo/package target: {snapshot.repo_url}
Git ref: {snapshot.ref}
{_dirty_note(snapshot.dirty_count)}
Command:

```bash
{command}
```

Expected proof shape:

- checked-out `code-puppy --help` succeeds
- checked-out `code-puppy-bootstrap detect --json` succeeds
- checked-out `code-puppy-bootstrap plan --profile auto` succeeds
- clean-run mode refuses contaminated environments if `--require-clean` is kept

Next optional validation:

- run `uv run --no-dev code-puppy -i` from the checkout
- attach DroidPuppy if phone-native tools are desired
- save the installer output as the handoff receipt

{_overlay_section(args.include_overlay, args.overlay_repo_url)}"""


def _published_packet(snapshot: RepoSnapshot, args: argparse.Namespace) -> str:
    version = _published_version(args)
    installer_url = _script_url(snapshot.repo_url, snapshot.ref, "onboard_android.sh")
    command = f"curl -fsSL {installer_url} | \\\n  bash -s -- --yes --version {version}"
    return f"""# Android Handoff Packet

Generated: {datetime.now(timezone.utc).isoformat()}
Android handoff lane: published-artifact
Package/version target: code-puppy {version}
Reference repo: {snapshot.repo_url}
Reference ref: {snapshot.ref}
{_dirty_note(snapshot.dirty_count)}
Command:

```bash
{command}
```

Expected proof shape:

- staged Android onboarding summary prints successfully
- lean Code Puppy install completes on Termux
- optional overlay/adb/browser readiness statuses are reported honestly
- `code-puppy -i` can be launched afterward if requested

Next optional validation:

- save the onboarding summary as the release receipt
- run `uvx --from code-puppy code-puppy-bootstrap plan --profile auto --json`
- attach DroidPuppy if phone-native tools are desired

{_overlay_section(args.include_overlay, args.overlay_repo_url)}"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a shareable Android onboarding packet for GitHub/Termux handoff.",
    )
    parser.add_argument(
        "--lane",
        choices=("checkout-ref", "published-artifact"),
        default="checkout-ref",
        help="Which Android handoff claim you want to make.",
    )
    parser.add_argument(
        "--repo-url", default="", help="Repo URL to hand another human."
    )
    parser.add_argument(
        "--ref", default="", help="Git ref/branch/tag to hand another human."
    )
    parser.add_argument(
        "--published-version",
        default="",
        help="Published code-puppy version for the published-artifact lane.",
    )
    parser.add_argument(
        "--overlay-repo-url",
        default=DEFAULT_OVERLAY_REPO_URL,
        help="Optional DroidPuppy overlay repo URL.",
    )
    parser.add_argument(
        "--no-overlay",
        action="store_false",
        dest="include_overlay",
        help="Omit the optional DroidPuppy overlay section.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Write the packet to a file instead of stdout-only.",
    )
    parser.set_defaults(include_overlay=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    snapshot = _snapshot(args)
    packet = (
        _checkout_packet(snapshot, args)
        if args.lane == "checkout-ref"
        else _published_packet(snapshot, args)
    )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(packet, encoding="utf-8")
        print(f"wrote {output_path}")
    print(packet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
