#!/usr/bin/env bash

set -u

REPO_URL="https://github.com/mpfaffenberger/code_puppy.git"
REPO_REF=""
ASSUME_YES=0
DRY_RUN=0
SKIP_UPGRADE=0
LAUNCH_AFTER_INSTALL=0
REQUIRE_CLEAN=0
CHECKOUT_DIR=""

usage() {
  cat <<'EOF'
Usage: scripts/install_termux_checkout.sh [options]

Fresh-Termux source-checkout installer/validator for Code Puppy.
Use this when the target under test is a branch/ref/checkout, not the published
PyPI artifact. It installs lean Termux prerequisites, clones the target repo,
syncs a no-dev environment, and verifies the checked-out code directly.

Options:
  --repo-url <url>      Git repository URL or local path to clone
  --ref <ref>           Branch, tag, or commit to checkout after clone
  --checkout-dir <dir>  Target clone directory (default: mktemp under $HOME)
  --yes                 Skip confirmation prompts
  --dry-run             Print the exact commands without executing them
  --skip-upgrade        Skip `pkg update && pkg upgrade`
  --launch              Start `uv run --no-dev code-puppy -i` after verification
  --no-launch           Verify only; do not launch interactive mode (default)
  --require-clean       Refuse to continue if clean-run contamination is detected
  --help                Show this help text

Examples:
  bash scripts/install_termux_checkout.sh --yes --ref main
  bash scripts/install_termux_checkout.sh --yes \
    --repo-url https://github.com/kvandre12-commits/code_puppy.git \
    --ref droidpuppy --require-clean
  curl -fsSL https://raw.githubusercontent.com/mpfaffenberger/code_puppy/main/scripts/install_termux_checkout.sh | \
    bash -s -- --yes --repo-url https://github.com/mpfaffenberger/code_puppy.git --ref main
EOF
}

log() {
  printf '%s\n' "$*"
}

warn() {
  printf 'warning: %s\n' "$*" >&2
}

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

have() {
  command -v "$1" >/dev/null 2>&1
}

confirm() {
  local prompt="$1"
  if [[ "$ASSUME_YES" -eq 1 || "$DRY_RUN" -eq 1 ]]; then
    log "$prompt [auto-yes]"
    return 0
  fi
  if [[ ! -t 0 ]]; then
    warn "$prompt [no TTY; rerun with --yes]"
    return 1
  fi
  read -r -p "$prompt [Y/n] " answer
  case "${answer:-}" in
    ""|y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

run_attempt() {
  local title="$1"
  local command="$2"

  log ""
  log "==> $title"
  log "+ $command"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    return 0
  fi
  if ! confirm "Proceed?"; then
    return 125
  fi
  bash -lc "$command"
}

run_step() {
  local title="$1"
  local command="$2"

  if ! run_attempt "$title" "$command"; then
    local code=$?
    if [[ "$code" -eq 125 ]]; then
      fail "required step skipped: $title"
    fi
    fail "required step failed: $title"
  fi
}

print_baseline() {
  log "Termux baseline snapshot"
  log "----------------------"
  log "uname -a: $(uname -a 2>/dev/null || true)"

  if have getprop; then
    log "android: $(getprop ro.build.version.release 2>/dev/null || true)"
  else
    log "android: getprop unavailable"
  fi

  if have termux-info; then
    log "termux-info:"
    termux-info || true
  else
    log "termux-info: unavailable"
  fi

  log "command -v code-puppy: $(command -v code-puppy 2>/dev/null || true)"
  log "command -v uv: $(command -v uv 2>/dev/null || true)"
  log "command -v python: $(command -v python 2>/dev/null || true)"
  log "command -v rustc: $(command -v rustc 2>/dev/null || true)"
  log "command -v clang: $(command -v clang 2>/dev/null || true)"
  log "VIRTUAL_ENV: ${VIRTUAL_ENV:-}"

  if have pkg; then
    log "pkg list-installed (selected):"
    pkg list-installed 2>/dev/null | grep -E '^(git|python|uv|ripgrep|proot|rust|clang)/' || true
  else
    log "pkg list-installed: pkg unavailable"
  fi
}

clean_run_contamination() {
  local contaminated=0

  if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    log "contamination: VIRTUAL_ENV is set -> ${VIRTUAL_ENV}"
    contaminated=1
  fi

  for binary in code-puppy uv rg proot rustc clang; do
    if have "$binary"; then
      log "contamination: $binary already present at $(command -v "$binary")"
      contaminated=1
    fi
  done

  if have pkg; then
    local pkg_hits
    pkg_hits="$(pkg list-installed 2>/dev/null | grep -E '^(uv|ripgrep|proot|rust|clang)/' || true)"
    if [[ -n "$pkg_hits" ]]; then
      log "contamination: preinstalled Termux packages detected"
      printf '%s\n' "$pkg_hits"
      contaminated=1
    fi
  fi

  return "$contaminated"
}

ensure_termux() {
  if have pkg; then
    return 0
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    warn "pkg not found; dry-run previewing anyway"
    return 0
  fi
  fail "this installer expects Termux (pkg not found)"
}

ensure_uv_path() {
  case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) export PATH="$HOME/.local/bin:$PATH" ;;
  esac
}

resolve_python() {
  if have python; then
    printf '%s' "python"
    return 0
  fi
  if have python3; then
    printf '%s' "python3"
    return 0
  fi
  fail "python not found on PATH after baseline install"
}

install_uv() {
  if ! run_attempt "Install uv from Termux packages" "pkg install -y uv"; then
    local code=$?
    if [[ "$code" -eq 125 ]]; then
      fail "required step skipped: Install uv from Termux packages"
    fi
    warn "pkg install uv failed; falling back to the official installer"
  fi

  ensure_uv_path
  if have uv; then
    return 0
  fi

  warn "uv still not on PATH after pkg install; trying official installer"
  if ! have curl; then
    run_step "Install curl for uv fallback" "pkg install -y curl"
  fi
  run_step "Install uv via official fallback" "curl -LsSf https://astral.sh/uv/install.sh | sh"
  ensure_uv_path
  have uv || fail "uv install completed, but `uv` is still not on PATH"
}

prepare_checkout_dir() {
  if [[ -n "$CHECKOUT_DIR" ]]; then
    return 0
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    CHECKOUT_DIR='$HOME/code-puppy-checkout-preview'
    return 0
  fi

  CHECKOUT_DIR="$(mktemp -d "$HOME/code-puppy-checkout.XXXXXX")"
}

verify_checkout_target() {
  if [[ -z "$CHECKOUT_DIR" ]]; then
    fail "internal error: checkout dir not prepared"
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    return 0
  fi

  if [[ -e "$CHECKOUT_DIR/.git" ]]; then
    return 0
  fi
  fail "expected a git checkout at $CHECKOUT_DIR"
}

main() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --repo-url)
        [[ $# -ge 2 ]] || fail "--repo-url requires a value"
        REPO_URL="$2"
        shift 2
        ;;
      --ref)
        [[ $# -ge 2 ]] || fail "--ref requires a value"
        REPO_REF="$2"
        shift 2
        ;;
      --checkout-dir)
        [[ $# -ge 2 ]] || fail "--checkout-dir requires a value"
        CHECKOUT_DIR="$2"
        shift 2
        ;;
      --yes)
        ASSUME_YES=1
        shift
        ;;
      --dry-run)
        DRY_RUN=1
        shift
        ;;
      --skip-upgrade)
        SKIP_UPGRADE=1
        shift
        ;;
      --launch)
        LAUNCH_AFTER_INSTALL=1
        shift
        ;;
      --no-launch)
        LAUNCH_AFTER_INSTALL=0
        shift
        ;;
      --require-clean)
        REQUIRE_CLEAN=1
        shift
        ;;
      --help|-h)
        usage
        exit 0
        ;;
      *)
        fail "unknown option: $1"
        ;;
    esac
  done

  prepare_checkout_dir
  local python_bin
  local quoted_repo_url
  local quoted_checkout_dir
  local quoted_ref

  log "Code Puppy Termux checkout installer"
  log "  repo    : $REPO_URL"
  log "  ref     : ${REPO_REF:-<default>}"
  log "  dir     : $CHECKOUT_DIR"
  log "  mode    : $([[ "$DRY_RUN" -eq 1 ]] && printf 'dry-run' || printf 'live')"
  log "  launch  : $([[ "$LAUNCH_AFTER_INSTALL" -eq 1 ]] && printf 'yes' || printf 'no')"
  log "  clean   : $([[ "$REQUIRE_CLEAN" -eq 1 ]] && printf 'required' || printf 'best-effort')"

  ensure_termux
  print_baseline

  if [[ "$REQUIRE_CLEAN" -eq 1 ]]; then
    log ""
    log "Checking clean-run contamination rules..."
    if clean_run_contamination; then
      fail "clean-run contamination detected; refusing to continue"
    fi
    log "No clean-run contamination detected."
  fi

  if [[ "$SKIP_UPGRADE" -eq 0 ]]; then
    run_step "Refresh Termux packages" "pkg update -y && pkg upgrade -y"
  fi

  run_step "Install baseline Termux packages" "pkg install -y python git"
  install_uv
  run_step "Install Termux native helpers" "pkg install -y ripgrep proot"

  ensure_uv_path
  python_bin="$(resolve_python)"
  quoted_repo_url=$(printf '%q' "$REPO_URL")
  quoted_checkout_dir=$(printf '%q' "$CHECKOUT_DIR")
  run_step "Clone Code Puppy checkout" "git clone $quoted_repo_url $quoted_checkout_dir"

  if [[ -n "$REPO_REF" ]]; then
    quoted_ref=$(printf '%q' "$REPO_REF")
    run_step "Checkout requested ref" "git -C $quoted_checkout_dir checkout $quoted_ref"
  fi

  verify_checkout_target

  local quoted_python_bin
  quoted_python_bin=$(printf '%q' "$python_bin")
  run_step "Sync lean source-checkout environment" \
    "cd $quoted_checkout_dir && uv sync --no-dev --python $quoted_python_bin"
  run_step "Verify checked-out CLI" \
    "cd $quoted_checkout_dir && uv run --no-dev --python $quoted_python_bin code-puppy --help"
  run_step "Inspect environment with checked-out bootstrap" \
    "cd $quoted_checkout_dir && uv run --no-dev --python $quoted_python_bin code-puppy-bootstrap detect --json"
  run_step "Build lean plan from checked-out bootstrap" \
    "cd $quoted_checkout_dir && uv run --no-dev --python $quoted_python_bin code-puppy-bootstrap plan --profile auto"

  if [[ "$LAUNCH_AFTER_INSTALL" -eq 1 ]]; then
    run_step "Launch checked-out Code Puppy" \
      "cd $quoted_checkout_dir && uv run --no-dev --python $quoted_python_bin code-puppy -i"
  fi

  log ""
  log "Checkout flow completed. This one actually tests the checked-out code instead of cosplaying as branch evidence."
}

main "$@"
