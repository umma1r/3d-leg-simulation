#!/bin/bash
# macOS double-click launcher for 3D Leg Simulation (Desktop only)
# Installs ONLY PyQt5 + VTK (no web libs) into a venv and runs 3dlegsim.py

set -euo pipefail

echo "=== 3D Leg Simulation (macOS Desktop) ==="

# Move to this script's folder
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ---- 1) Find a usable Python 3 interpreter --------------------
for CAND in python3.11 python3.12 python3.10 python3; do
  if command -v "$CAND" >/dev/null 2>&1; then
    PY="$CAND"
    break
  fi
done

if [ -z "${PY:-}" ]; then
  osascript -e 'display dialog "Python 3.11 (or 3.10/3.12) is required.\nClick OK to open python.org and install Python 3.11.\nThen double-click this file again." buttons {"OK"} default button "OK"'
  open "https://www.python.org/downloads/release/python-3119/"
  exit 0
fi

echo "Using system Python: $PY ($($PY -V))"

# ---- 2) Create and activate a venv -----------------------------
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment with $PY …"
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source ".venv/bin/activate"
VENV_PY="$(python -c 'import sys; print(sys.executable)')"
echo "Venv interpreter: $VENV_PY"

# ---- 3) Install ONLY desktop deps (PyQt5 + VTK) ----------------
PYQT_VER="5.15.11"
VTK_VER="9.3.0"
echo "Installing PyQt5==$PYQT_VER and vtk==$VTK_VER …"
"$VENV_PY" -m pip install --upgrade pip wheel
if ! "$VENV_PY" -m pip install --only-binary=:all: "PyQt5==$PYQT_VER" "vtk==$VTK_VER"; then
  echo "Binary wheels unavailable; attempting source-compatible install…"
  "$VENV_PY" -m pip install "PyQt5==$PYQT_VER" "vtk==$VTK_VER"
fi

# ---- 4) Sanity import test -------------------------------------
"$VENV_PY" - <<'PY'
import sys
print("Python:", sys.version)
try:
    import PyQt5, vtk
    print("Imports OK: PyQt5 and vtk")
except Exception as e:
    print("Dependency import failed:", repr(e))
    raise SystemExit(1)
PY

# ---- 5) Launch the app (filtering CFURL warnings) ---------------
echo "Launching 3dlegsim.py …"
LOGFILE=".last_run.log"
set +e

# Run and filter the noisy CFURL warning from the console,
# but keep all other stderr in the log.
"$VENV_PY" 3dlegsim.py 2>"$LOGFILE" | grep -v "cfurlcopyresourcepropertyforkey" || true

STATUS=${PIPESTATUS[0]}
set -e

if [ $STATUS -ne 0 ]; then
  echo "The app exited with status $STATUS."
  echo "---- Tail of $LOGFILE ----"
  tail -n 80 "$LOGFILE" || true
  osascript -e 'display dialog "The app failed to launch. See .last_run.log for details." buttons {"OK"} default button "OK"'
else
  echo "App closed normally."
fi
