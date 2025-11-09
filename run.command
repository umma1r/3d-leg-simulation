#!/bin/bash
# macOS double-click launcher for 3D Leg Simulation
set -euo pipefail

echo "=== 3D Leg Simulation Setup and Launch (macOS) ==="

# Find repo dir (the folder containing this script) and cd there
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Prefer an existing python3; if missing, offer to install
if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  osascript -e 'display dialog "Python 3 is required. Click OK to open python.org. Install Python 3, then double-click this file again." buttons {"OK"} default button "OK"'
  open "https://www.python.org/downloads/"
  exit 0
fi

# Create venv if missing
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment…"
  "$PY" -m venv .venv
fi

# Activate venv (bash-compatible)
# shellcheck disable=SC1091
source ".venv/bin/activate"

echo "Upgrading pip and installing dependencies…"
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "Launching desktop simulation…"
python 3dlegsim.py

echo "Simulation closed. You can close this window."
