"""Interactive, environment-aware install wizard for Code Puppy.

The bootstrap planner (``code_puppy.bootstrap_profiles``) decides what should
be installed. This module is the wizard: it walks an operator -- especially an
Android/Termux newcomer -- through doing it, one confirmed step at a time, then
verifies and reconciles the result.

Design rules honored here:
- stdlib-only (``subprocess``/``shutil``) so it runs before any heavy deps
- destructive/state-altering steps are gated behind explicit confirmation
- ``--dry-run`` never executes; ``--yes`` auto-confirms for automation
- the wizard always ends with a verification + reconciliation summary
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

from code_puppy.bootstrap_profiles import build_install_plan, detect_environment


@dataclass
class WizardStep:
    key: str
    title: str
    command: str
    explanation: str
    is_satisfied: Callable[[], bool] = field(default=lambda: False)
    required: bool = True


@dataclass
class StepOutcome:
    key: str
    status: str
    detail: str = ""


def _has(binary: str) -> bool:
    return shutil.which(binary) is not None


def build_steps(profile: str | None = None) -> tuple[list[WizardStep], dict[str, Any]]:
    plan = build_install_plan(requested_profile=profile)
    env = plan["environment"]
    steps: list[WizardStep] = []

    if not env.get("has_uv"):
        if env.get("is_termux") or env.get("is_android"):
            uv_cmd = "pip install uv"
        else:
            uv_cmd = "curl -LsSf https://astral.sh/uv/install.sh | sh"
        steps.append(
            WizardStep(
                key="uv",
                title="Install the uv package manager",
                command=uv_cmd,
                explanation="uv installs and runs Code Puppy in an isolated tool env.",
                is_satisfied=lambda: _has("uv"),
            )
        )

    missing = plan.get("missing_system_packages") or []
    if missing:
        steps.append(
            WizardStep(
                key="system_packages",
                title=f"Install Termux system packages: {', '.join(missing)}",
                command=f"pkg install -y {' '.join(missing)}",
                explanation=(
                    "These ship as native binaries (no Python wheels on Android), "
                    "so Code Puppy shells out to them instead of bundling them."
                ),
                is_satisfied=lambda missing=missing: all(
                    _has("rg" if item == "ripgrep" else item) for item in missing
                ),
            )
        )

    steps.append(
        WizardStep(
            key="code_puppy",
            title=f"Install Code Puppy ({plan['package_spec']})",
            command=plan["install_command"],
            explanation=plan["description"],
            is_satisfied=lambda: False,
        )
    )

    return steps, plan


def _confirm(prompt: str, *, assume_yes: bool) -> bool:
    if assume_yes:
        print(f"{prompt} [auto-yes]")
        return True
    if not sys.stdin.isatty():
        print(f"{prompt} [no TTY -- skipping; pass --yes to auto-run]")
        return False
    try:
        answer = input(f"{prompt} [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer in ("", "y", "yes")


def _run_command(command: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=1800,
        )
    except subprocess.TimeoutExpired:
        return 124, "timed out after 1800s"
    except Exception as exc:
        return 1, f"failed to launch: {exc}"
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output.strip()


def _verify(_plan: dict[str, Any]) -> StepOutcome:
    if not _has("code-puppy"):
        return StepOutcome(
            "verify",
            "failed",
            "`code-puppy` not found on PATH after install.",
        )
    code, out = _run_command("code-puppy --help")
    if code != 0:
        tail = out.splitlines()[-3:] if out else []
        return StepOutcome("verify", "failed", "; ".join(tail) or f"exit {code}")
    return StepOutcome("verify", "done", "`code-puppy --help` runs cleanly.")


def run_wizard(
    *,
    profile: str | None = None,
    assume_yes: bool = False,
    dry_run: bool = False,
) -> int:
    steps, plan = build_steps(profile)
    env = plan["environment"]

    print("Code Puppy install wizard")
    print(f"  profile : {plan['profile']}")
    print(
        "  device  : "
        f"{env['platform_system']} {env['platform_release']} ({env['platform_machine']})"
    )
    print(f"  python  : {env['python_version']}")
    print(f"  steps   : {len(steps)}")
    if dry_run:
        print("  mode    : DRY-RUN (nothing will be executed)")
    print()

    outcomes: list[StepOutcome] = []

    for index, step in enumerate(steps, start=1):
        print(f"[{index}/{len(steps)}] {step.title}")
        print(f"      why: {step.explanation}")
        print(f"      run: {step.command}")

        if step.is_satisfied():
            print("      -> already satisfied, skipping.\n")
            outcomes.append(StepOutcome(step.key, "satisfied"))
            continue

        if dry_run:
            print("      -> dry-run, not executed.\n")
            outcomes.append(StepOutcome(step.key, "dry-run"))
            continue

        if not _confirm("      proceed?", assume_yes=assume_yes):
            print("      -> skipped.\n")
            outcomes.append(StepOutcome(step.key, "skipped"))
            if step.required:
                print(
                    "      (this step is required -- later steps may fail without it)\n"
                )
            continue

        code, out = _run_command(step.command)
        if code == 0:
            print("      -> done.\n")
            outcomes.append(StepOutcome(step.key, "done"))
        else:
            tail = "\n        ".join(out.splitlines()[-5:]) if out else f"exit {code}"
            print(f"      -> FAILED (exit {code}):\n        {tail}\n")
            outcomes.append(StepOutcome(step.key, "failed", f"exit {code}"))
            if step.required:
                print("Required step failed -- stopping. Fix the above and re-run.\n")
                _print_summary(outcomes, verify=None)
                return 1

    verify = None
    if not dry_run:
        verify = _verify(plan)
        symbol = "OK" if verify.status == "done" else "FAILED"
        print(f"Verification: {symbol} -- {verify.detail}\n")

    _print_summary(outcomes, verify=verify)

    failed = any(outcome.status == "failed" for outcome in outcomes)
    if verify is not None and verify.status == "failed":
        failed = True
    return 1 if failed else 0


def _print_summary(outcomes: list[StepOutcome], *, verify: StepOutcome | None) -> None:
    print("Summary (state reconciliation):")
    for outcome in outcomes:
        line = f"  - {outcome.key}: {outcome.status}"
        if outcome.detail:
            line += f" ({outcome.detail})"
        print(line)
    if verify is not None:
        line = f"  - verify: {verify.status}"
        if verify.detail:
            line += f" ({verify.detail})"
        print(line)
    if verify is not None and verify.status == "done":
        print("\nAll set -- run it with:  code-puppy -i")


def detect_summary() -> dict[str, Any]:
    return detect_environment()
