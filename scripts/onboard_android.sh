#!/usr/bin/env bash

set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORE_INSTALLER="$ROOT_DIR/scripts/install_termux.sh"
DEFAULT_OVERLAY_REPO_URL="https://github.com/kvandre12-commits/DroidPuppy"
DEFAULT_OVERLAY_LOCAL_DIR="$ROOT_DIR/DroidPuppy"
DEFAULT_USER_PLUGIN_DIR="$HOME/.code_puppy/plugins"

PACKAGE_VERSION=""
ASSUME_YES=0
DRY_RUN=0
SKIP_UPGRADE=0
SKIP_OVERLAY=0
SKIP_ADB_INSTALL=0
LAUNCH_AT_END=0
OVERLAY_DIR=""
OVERLAY_REPO_URL="$DEFAULT_OVERLAY_REPO_URL"
TMP_OVERLAY_DIR=""

CORE_STATUS="PENDING"
CORE_DETAIL=""
OVERLAY_STATUS="PENDING"
OVERLAY_DETAIL=""
LOCAL_STATUS="PENDING"
LOCAL_DETAIL=""
ADB_STATUS="PENDING"
ADB_DETAIL=""
BROWSER_STATUS="PENDING"
BROWSER_DETAIL=""

NEXT_ACTIONS=()

usage() {
  cat <<'EOF'
Usage: scripts/onboard_android.sh [options]

Professional Android first-run onboarding for Code Puppy + DroidPuppy.

This command owns the milestone-1 journey:
  1. lean Code Puppy install on Termux
  2. optional DroidPuppy overlay attach
  3. adb/android-tools detection or install
  4. staged readiness summary with next actions

Options:
  --version <ver>         Install an exact published Code Puppy version
  --yes                   Skip confirmation prompts
  --dry-run               Print the commands without executing them
  --skip-upgrade          Skip `pkg update && pkg upgrade`
  --skip-overlay          Do not install the DroidPuppy overlay
  --overlay-dir <path>    Use an existing DroidPuppy checkout instead of cloning
  --overlay-repo-url <u>  Override the DroidPuppy git clone URL
  --skip-adb-install      Detect adb only; do not install android-tools if missing
  --launch                Start `code-puppy -i` after the final summary
  --no-launch             Keep onboarding verify-only (default)
  --help                  Show this help text

Examples:
  bash scripts/onboard_android.sh --yes
  bash scripts/onboard_android.sh --yes --version 0.0.569
  curl -fsSL https://raw.githubusercontent.com/mpfaffenberger/code_puppy/main/scripts/onboard_android.sh | \
    bash -s -- --yes --version 0.0.569
EOF
}

log() {
  printf '%s\n' "$*"
}

warn() {
  printf 'warning: %s\n' "$*" >&2
}

have() {
  command -v "$1" >/dev/null 2>&1
}

cleanup() {
  if [[ -n "$TMP_OVERLAY_DIR" && -d "$TMP_OVERLAY_DIR" ]]; then
    rm -rf "$TMP_OVERLAY_DIR"
  fi
}

trap cleanup EXIT

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

run_required_step() {
  local title="$1"
  local command="$2"
  run_attempt "$title" "$command"
  local code=$?
  if [[ "$code" -eq 0 ]]; then
    return 0
  fi
  if [[ "$code" -eq 125 ]]; then
    warn "required step skipped: $title"
  else
    warn "required step failed: $title"
  fi
  return 1
}

run_optional_step() {
  local title="$1"
  local command="$2"
  run_attempt "$title" "$command"
  local code=$?
  if [[ "$code" -eq 0 ]]; then
    return 0
  fi
  if [[ "$code" -eq 125 ]]; then
    return 125
  fi
  return 1
}

quote_cmd() {
  printf '%q ' "$@"
}

resolve_python() {
  if have python; then
    printf 'python'
    return 0
  fi
  if have python3; then
    printf 'python3'
    return 0
  fi
  return 1
}

plugin_probe_path() {
  printf '%s/android_setup_helper/register_callbacks.py' "$DEFAULT_USER_PLUGIN_DIR"
}

overlay_is_installed() {
  [[ -f "$(plugin_probe_path)" ]]
}

local_android_status() {
  local missing=()
  local command
  for command in am pm cmd; do
    if ! have "$command"; then
      missing+=("$command")
    fi
  done
  if [[ ${#missing[@]} -eq 0 ]]; then
    LOCAL_STATUS="READY"
    LOCAL_DETAIL="Core Android commands available (am/pm/cmd)."
    return
  fi
  LOCAL_STATUS="BLOCKED"
  LOCAL_DETAIL="Missing Android commands: ${missing[*]}"
  NEXT_ACTIONS+=("Run this onboarding flow from Android Termux; local Android commands are unavailable here.")
}

adb_device_count() {
  if ! have adb; then
    printf '0'
    return
  fi
  adb devices 2>/dev/null | awk 'NR > 1 && NF > 0 { count += 1 } END { print count + 0 }'
}

browser_inventory() {
  local listing=""
  if have cmd; then
    listing="$(cmd package list packages 2>/dev/null || true)"
  elif have pm; then
    listing="$(pm list packages 2>/dev/null || true)"
  fi

  local browsers=()
  if printf '%s\n' "$listing" | grep -q 'package:com.brave.browser'; then
    browsers+=("Brave")
  fi
  if printf '%s\n' "$listing" | grep -q 'package:com.android.chrome'; then
    browsers+=("Chrome")
  fi
  if printf '%s\n' "$listing" | grep -q 'package:org.mozilla.firefox'; then
    browsers+=("Firefox")
  fi

  if [[ ${#browsers[@]} -eq 0 ]]; then
    BROWSER_STATUS="BLOCKED"
    BROWSER_DETAIL="No supported browser package detected via pm/cmd."
    NEXT_ACTIONS+=("Install Brave or Chrome on the Android device before expecting browser/CDP flows to work.")
    return
  fi

  BROWSER_STATUS="READY"
  BROWSER_DETAIL="Detected browsers: ${browsers[*]}"
}

summary_line() {
  printf '  %-26s %s\n' "$1" "$2"
  if [[ -n "$3" ]]; then
    printf '    %s\n' "$3"
  fi
}

print_summary() {
  log ""
  log "Android Onboarding Summary"
  log "-------------------------"
  summary_line "Core Code Puppy:" "$CORE_STATUS" "$CORE_DETAIL"
  summary_line "DroidPuppy overlay:" "$OVERLAY_STATUS" "$OVERLAY_DETAIL"
  summary_line "Android local utilities:" "$LOCAL_STATUS" "$LOCAL_DETAIL"
  summary_line "ADB / Wireless Debugging:" "$ADB_STATUS" "$ADB_DETAIL"
  summary_line "Browser readiness:" "$BROWSER_STATUS" "$BROWSER_DETAIL"

  if [[ ${#NEXT_ACTIONS[@]} -gt 0 ]]; then
    log ""
    log "Next best actions:"
    local index=1
    local action
    for action in "${NEXT_ACTIONS[@]}"; do
      printf '  %d. %s\n' "$index" "$action"
      index=$((index + 1))
    done
  fi
}

assess_core() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    CORE_STATUS="DRY-RUN"
    CORE_DETAIL="Core Termux install was previewed but not executed."
    return
  fi
  if have code-puppy; then
    CORE_STATUS="READY"
    CORE_DETAIL="`code-puppy` is on PATH and core install completed."
    return
  fi
  CORE_STATUS="FAIL"
  CORE_DETAIL="`code-puppy` was not found on PATH after core install."
  NEXT_ACTIONS+=("Re-run the core installer and verify that ~/.local/bin is on PATH.")
}

resolve_overlay_source() {
  if [[ -n "$OVERLAY_DIR" ]]; then
    printf '%s' "$OVERLAY_DIR"
    return
  fi
  if [[ -d "$DEFAULT_OVERLAY_LOCAL_DIR" ]]; then
    printf '%s' "$DEFAULT_OVERLAY_LOCAL_DIR"
    return
  fi
  printf ''
}

install_overlay_stage() {
  if [[ "$SKIP_OVERLAY" -eq 1 ]]; then
    OVERLAY_STATUS="SKIPPED"
    OVERLAY_DETAIL="Overlay install was intentionally skipped."
    NEXT_ACTIONS+=("If you want Android-native tools later, install the DroidPuppy overlay and re-run onboarding.")
    return 0
  fi

  local python_cmd
  if ! python_cmd="$(resolve_python)"; then
    OVERLAY_STATUS="FAIL"
    OVERLAY_DETAIL="Python was not found, so the overlay installer could not run."
    NEXT_ACTIONS+=("Install Python in Termux first, then re-run onboarding.")
    return 1
  fi

  local source_dir
  source_dir="$(resolve_overlay_source)"

  if [[ -z "$source_dir" ]]; then
    TMP_OVERLAY_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t code-puppy-android-onboard)"
    local clone_target="$TMP_OVERLAY_DIR/DroidPuppy"
    run_optional_step \
      "Fetch DroidPuppy overlay source" \
      "git clone --depth 1 $(printf '%q' "$OVERLAY_REPO_URL") $(printf '%q' "$clone_target")"
    local code=$?
    if [[ "$code" -ne 0 ]]; then
      if [[ "$code" -eq 125 ]]; then
        OVERLAY_STATUS="SKIPPED"
        OVERLAY_DETAIL="Overlay source fetch was skipped."
        NEXT_ACTIONS+=("Clone $OVERLAY_REPO_URL and run python scripts/install_overlay.py --overwrite when you want Android-native tools.")
        return 0
      fi
      OVERLAY_STATUS="FAIL"
      OVERLAY_DETAIL="Failed to fetch the DroidPuppy overlay source."
      NEXT_ACTIONS+=("Clone $OVERLAY_REPO_URL manually and run python scripts/install_overlay.py --overwrite.")
      return 1
    fi
    source_dir="$clone_target"
  fi

  local install_command
  install_command="$(printf '%q ' "$python_cmd" "$source_dir/scripts/install_overlay.py")--overwrite"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    install_command="$install_command --dry-run"
  fi

  run_optional_step "Install DroidPuppy overlay" "$install_command"
  local code=$?
  if [[ "$code" -ne 0 ]]; then
    if [[ "$code" -eq 125 ]]; then
      OVERLAY_STATUS="SKIPPED"
      OVERLAY_DETAIL="Overlay install was skipped."
      NEXT_ACTIONS+=("Re-run onboarding without --skip-overlay if you want Android-native commands.")
      return 0
    fi
    OVERLAY_STATUS="FAIL"
    OVERLAY_DETAIL="The overlay installer failed."
    NEXT_ACTIONS+=("Run python $source_dir/scripts/install_overlay.py --overwrite manually and inspect the error output.")
    return 1
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    OVERLAY_STATUS="DRY-RUN"
    OVERLAY_DETAIL="Overlay install was previewed but not executed."
    return 0
  fi

  if overlay_is_installed; then
    OVERLAY_STATUS="READY"
    OVERLAY_DETAIL="Detected Android overlay plugin files under $DEFAULT_USER_PLUGIN_DIR."
    return 0
  fi

  OVERLAY_STATUS="FAIL"
  OVERLAY_DETAIL="Overlay install ran, but the expected plugin probe file was not found."
  NEXT_ACTIONS+=("Inspect $DEFAULT_USER_PLUGIN_DIR and confirm the DroidPuppy plugins were copied there.")
  return 1
}

install_adb_stage() {
  if have adb; then
    local count=0
    if [[ "$DRY_RUN" -eq 0 ]]; then
      count="$(adb_device_count)"
    fi
    if [[ "$count" -gt 0 ]]; then
      ADB_STATUS="READY"
      ADB_DETAIL="adb is installed and sees $count device(s)."
    else
      ADB_STATUS="BLOCKED"
      ADB_DETAIL="adb is installed, but no paired device is connected yet."
      NEXT_ACTIONS+=("Enable Developer options -> Wireless debugging, then run adb pair <ip>:<pair_port> and adb connect <ip>:<connect_port>.")
    fi
    return 0
  fi

  if [[ "$SKIP_ADB_INSTALL" -eq 1 ]]; then
    ADB_STATUS="BLOCKED"
    ADB_DETAIL="adb is missing and install was intentionally skipped."
    NEXT_ACTIONS+=("Install adb in Termux with: pkg install android-tools")
    return 0
  fi

  run_optional_step "Install adb / android-tools" "pkg install -y android-tools"
  local code=$?
  if [[ "$code" -ne 0 ]]; then
    if [[ "$code" -eq 125 ]]; then
      ADB_STATUS="SKIPPED"
      ADB_DETAIL="adb install was skipped."
      NEXT_ACTIONS+=("Install adb in Termux with: pkg install android-tools")
      return 0
    fi
    ADB_STATUS="FAIL"
    ADB_DETAIL="Failed to install android-tools."
    NEXT_ACTIONS+=("Run pkg install android-tools manually, then re-run onboarding.")
    return 1
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    ADB_STATUS="DRY-RUN"
    ADB_DETAIL="adb install was previewed but not executed."
    NEXT_ACTIONS+=("After the real install, pair Wireless Debugging and re-run onboarding to verify adb connectivity.")
    return 0
  fi

  if have adb; then
    ADB_STATUS="BLOCKED"
    ADB_DETAIL="adb is installed. Next step is pairing Wireless Debugging."
    NEXT_ACTIONS+=("Enable Wireless Debugging and run adb pair/connect from Termux.")
    return 0
  fi

  ADB_STATUS="FAIL"
  ADB_DETAIL="android-tools reported success, but `adb` is still not on PATH."
  NEXT_ACTIONS+=("Verify the android-tools install and ensure Termux PATH is sane.")
  return 1
}

run_core_stage() {
  local -a args
  args=("bash" "$CORE_INSTALLER" "--no-launch")
  if [[ -n "$PACKAGE_VERSION" ]]; then
    args+=("--version" "$PACKAGE_VERSION")
  fi
  if [[ "$ASSUME_YES" -eq 1 ]]; then
    args+=("--yes")
  fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    args+=("--dry-run")
  fi
  if [[ "$SKIP_UPGRADE" -eq 1 ]]; then
    args+=("--skip-upgrade")
  fi

  local core_command
  core_command="$(quote_cmd "${args[@]}")"
  run_required_step "Install lean Code Puppy core on Termux" "$core_command"
}

main() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --version)
        [[ $# -ge 2 ]] || { warn "--version requires a value"; exit 1; }
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
      --skip-overlay)
        SKIP_OVERLAY=1
        shift
        ;;
      --overlay-dir)
        [[ $# -ge 2 ]] || { warn "--overlay-dir requires a value"; exit 1; }
        OVERLAY_DIR="$2"
        shift 2
        ;;
      --overlay-repo-url)
        [[ $# -ge 2 ]] || { warn "--overlay-repo-url requires a value"; exit 1; }
        OVERLAY_REPO_URL="$2"
        shift 2
        ;;
      --skip-adb-install)
        SKIP_ADB_INSTALL=1
        shift
        ;;
      --launch)
        LAUNCH_AT_END=1
        shift
        ;;
      --no-launch)
        LAUNCH_AT_END=0
        shift
        ;;
      --help|-h)
        usage
        exit 0
        ;;
      *)
        warn "unknown option: $1"
        exit 1
        ;;
    esac
  done

  log "Android onboarding command"
  log "  package version : ${PACKAGE_VERSION:-latest}"
  log "  mode            : $([[ "$DRY_RUN" -eq 1 ]] && printf 'dry-run' || printf 'live')"
  log "  overlay         : $([[ "$SKIP_OVERLAY" -eq 1 ]] && printf 'skip' || printf 'install')"
  log "  adb             : $([[ "$SKIP_ADB_INSTALL" -eq 1 ]] && printf 'detect-only' || printf 'install-if-missing')"
  log "  launch          : $([[ "$LAUNCH_AT_END" -eq 1 ]] && printf 'after-summary' || printf 'no')"

  local overall_ok=0

  if ! run_core_stage; then
    overall_ok=1
  fi
  assess_core

  local_android_status

  if ! install_overlay_stage; then
    overall_ok=1
  fi

  if ! install_adb_stage; then
    overall_ok=1
  fi

  browser_inventory
  print_summary

  if [[ "$DRY_RUN" -eq 0 && "$LAUNCH_AT_END" -eq 1 && "$CORE_STATUS" == "READY" ]]; then
    if ! run_optional_step "Launch Code Puppy" "code-puppy -i"; then
      warn "launch was requested but failed"
      overall_ok=1
    fi
  fi

  if [[ "$overall_ok" -ne 0 ]]; then
    log ""
    log "Android onboarding finished with some teeth marks. Re-check the summary above."
    exit 1
  fi

  log ""
  log "Android onboarding completed. Professional-ish now."
}

main "$@"
