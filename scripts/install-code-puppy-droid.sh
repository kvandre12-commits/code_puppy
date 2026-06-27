#!/usr/bin/env sh
set -eu

PACKAGE_SPEC="${CODE_PUPPY_PACKAGE_SPEC:-code-puppy}"
PYTHON_BIN="${PYTHON_BIN:-python}"

info() { printf '%s\n' "[code-puppy-droid] $*"; }

install_uv() {
  if command -v uv >/dev/null 2>&1; then
    return 0
  fi

  if command -v pkg >/dev/null 2>&1; then
    info "Installing uv from Termux packages"
    if pkg install -y uv; then
      return 0
    fi
  fi

  info "Falling back to pip install uv"
  "$PYTHON_BIN" -m pip install --upgrade uv
}

info "Installing Code Puppy Droid beta runtime"

if command -v pkg >/dev/null 2>&1; then
  info "Detected Termux pkg; installing base packages"
  pkg update -y
  pkg install -y python git android-tools termux-api ripgrep proot
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  info "python not found. Install Python first, then rerun this script."
  exit 1
fi

info "Upgrading pip"
"$PYTHON_BIN" -m pip install --upgrade pip

install_uv

if command -v uv >/dev/null 2>&1; then
  info "Installing $PACKAGE_SPEC with uv"
  uv tool install --refresh "$PACKAGE_SPEC"
else
  info "Installing $PACKAGE_SPEC with pip"
  "$PYTHON_BIN" -m pip install --upgrade "$PACKAGE_SPEC"
fi

info "Install complete"
info "Run the guided lean bootstrap with: code-puppy-bootstrap wizard"
info "Inspect the device first with: code-puppy-bootstrap detect --json"
info "Start Code Puppy with: code-puppy -i"
info "Inside Code Puppy, open the Droid viewer with: /droid open"
info "Then inspect bridge permissions with: /bridge list"
