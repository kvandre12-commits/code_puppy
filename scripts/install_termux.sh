#!/usr/bin/env bash

set -u

PACKAGE_NAME="code-puppy"
PACKAGE_VERSION=""
ASSUME_YES=0
DRY_RUN=0
SKIP_UPGRADE=0
LAUNCH_AFTER_INSTALL=1
REQUIRE_CLEAN=0

usage() {
  cat <<'EOF'
Usage: scripts/install_termux.sh [options]

Fresh-user Termux installer for Code Puppy.

Options:
  --version <ver>     Install an exact published version (for acceptance runs)
  --yes               Skip confirmation prompts
  --dry-run           Print the exact commands without executing them
  --skip-upgrade      Skip `pkg update && pkg upgrade`
  --no-launch         Verify install but do not run `code-puppy -i`
  --require-clean     Refuse to continue if clean-run contamination is detected
  --help              Show this help text

Examples:
  bash scripts/install_termux.sh --yes
  bash scripts/install_termux.sh --yes --version 0.0.569 --require-clean
  curl -fsSL https://raw.githubusercontent.com/mpfaffenberger/code_puppy/main/scripts/install_termux.sh | \
    bash -s -- --yes --version 0.0.569 --require-clean
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

package_ref() {
  if [[ -n "$PACKAGE_VERSION" ]]; then
    printf '%s==%s' "$PACKAGE_NAME" "$PACKAGE_VERSION"
    return
  fi
  printf '%s' "$PACKAGE_NAME"
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
  fail "this installer expects Termux (`pkg` not found)"
}

ensure_uv_path() {
  case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) export PATH="$HOME/.local/bin:$PATH" ;;
  esac
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

verify_install() {
  ensure_uv_path

  if [[ "$DRY_RUN" -eq 1 ]]; then
    log ""
    log "Verification preview"
    log "+ command -v code-puppy"
    log "+ code-puppy --help"
    if [[ "$LAUNCH_AFTER_INSTALL" -eq 1 ]]; then
      log "+ code-puppy -i"
    fi
    return 0
  fi

  if ! have code-puppy; then
    fail "`code-puppy` not found on PATH after install (expected under ~/.local/bin)"
  fi

  run_step "Verify installed CLI" "code-puppy --help"

  if [[ "$LAUNCH_AFTER_INSTALL" -eq 1 ]]; then
    run_step "Launch Code Puppy" "code-puppy -i"
  fi
}

main() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --version)
        [[ $# -ge 2 ]] || fail "--version requires a value"
        PACKAGE_VERSION="$2"
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

  local package
  package="$(package_ref)"

  log "Code Puppy Termux installer"
  log "  package : $package"
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

  local quoted_package
  quoted_package=$(printf '%q' "$package")

  run_step "Inspect environment with bootstrap planner" \
    "uvx --from $quoted_package code-puppy-bootstrap detect --json"
  run_step "Build lean install plan" \
    "uvx --from $quoted_package code-puppy-bootstrap plan --profile auto"
  run_step "Install Termux native helpers" "pkg install -y ripgrep proot"
  run_step "Install Code Puppy" "uv tool install --refresh $quoted_package"

  verify_install

  log ""
  log "Install flow completed. Less cursed now."
}

main "$@"
