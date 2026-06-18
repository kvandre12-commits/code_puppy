#!/usr/bin/env sh
set -eu

PACKAGE_SPEC="${CODE_PUPPY_PACKAGE_SPEC:-code-puppy}"
PYTHON_BIN="${PYTHON_BIN:-python}"

info() { printf '%s\n' "[code-puppy-droid] $*"; }

info "Installing Code Puppy Droid beta runtime"

if command -v pkg >/dev/null 2>&1; then
  info "Detected Termux pkg; installing base packages"
  pkg update -y
  pkg install -y python git android-tools termux-api
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  info "python not found. Install Python first, then rerun this script."
  exit 1
fi

info "Upgrading pip"
"$PYTHON_BIN" -m pip install --upgrade pip

info "Installing $PACKAGE_SPEC"
"$PYTHON_BIN" -m pip install --upgrade "$PACKAGE_SPEC"

info "Install complete"
info "Start Code Puppy with: code-puppy -i"
info "Inside Code Puppy, open the Droid viewer with: /droid open"
info "Then inspect bridge permissions with: /bridge list"
