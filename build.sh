#!/usr/bin/env bash
# Build the Android APK. Run this inside WSL (Ubuntu) or any Linux machine.
# On Windows it will NOT work: buildozer/python-for-android are Linux-only.
#
# Prerequisites (run once, inside Ubuntu):
#   sudo apt update
#   sudo apt install -y python3 python3-venv python3-pip git zip unzip openjdk-17-jdk
set -e

cd "$(dirname "$0")"

# Use a venv to avoid PEP 668 (externally-managed-environment) on modern Ubuntu.
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
. .venv/bin/activate

echo "==> Installing buildozer and cython (required for the build)"
pip install --upgrade pip setuptools wheel
pip install buildozer cython

echo "==> Building debug APK (first run downloads Android SDK/NDK, takes a while)"
buildozer -v android debug

echo
echo "Done. APK(s) are in: $(pwd)/bin/"
ls -1 bin/*.apk 2>/dev/null || true
