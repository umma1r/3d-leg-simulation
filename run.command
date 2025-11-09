#!/bin/bash
# macOS double-click launcher for 3D Leg Simulation (Desktop only)
# Installs ONLY PyQt5 + VTK into a venv, then runs 3dlegsim.py.
# Filters the benign CFURL "no scheme" noise but preserves all other logs.

set -euo pipefail

echo "=== 3D Leg Simulation (macOS Desktop) ==="

# cd to this script's folder
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 1) Pick a usable Python (prefer 3.11; 3.12/3.10 also fine)
for CAND in python3.11 python3.12 python3.10 python3; do
  if command -v "$CAND" >/dev/null 2>&1; then PY="$CAND"; break; fi
done
if [ -z "${PY:-}" ]; then
  osascript -e 'display dialog "Python 3 is required.\nClick OK to open python.org and install Python 3.11.\nThen double-click this file again." buttons {"OK"} default button "OK"'
  open "https://www.python.org/downloads/release/python-3119/"
  exit 0
fi
echo "Using system Python: $PY ($($PY -V))"

# 2) Create / activate venv with that interpreter
[ -d .venv ] || "$PY" -m venv .venv
# shellcheck disable=SC1091
source ".venv/bin/activate"

# prefer pythonw if available (GUI launcher on macOS), else python
VENV_PY="$(python -c 'import sys; print(sys.executable)')"
if [ -x "$(dirname "$VENV_PY")/pythonw" ]; then
  VENV_PY="$(dirname "$VENV_PY")/pythonw"
fi
echo "Venv interpreter: $VENV_PY"

# 3) Install ONLY desktop deps (no web libs)
PYQT_VER="5.15.11"
VTK_VER="9.3.0"
echo "Installing PyQt5==$PYQT_VER and vtk==$VTK_VER …"
"$VENV_PY" -m pip install --upgrade pip wheel
if ! "$VENV_PY" -m pip install --only-binary=:all: "PyQt5==$PYQT_VER" "vtk==$VTK_VER"; then
  echo "Binary wheels unavailable; attempting source-compatible install…"
  "$VENV_PY" -m pip install "PyQt5==$PYQT_VER" "vtk==$VTK_VER"
fi

# 4) Quick import sanity check (same interpreter)
"$VENV_PY" - <<'PY'
import sys
print("Python:", sys.version)
try:
    import PyQt5, vtk   # noqa: F401
    print("Imports OK: PyQt5 and vtk")
except Exception as e:
    print("Dependency import failed:", repr(e))
    raise SystemExit(1)
PY

# 5) Launch app; filter CFURL noise from BOTH stdout+stderr, still save a full log
echo "Launching 3dlegsim.py …"
LOGFILE=".last_run.log"
set +e

# If you also want to suppress Qt debug spam, uncomment the next line:
# export QT_LOGGING_RULES="*.debug=false;qt.qpa.*=false"

# Run, capture stdout+stderr, filter the CFURL 'no scheme' variants to console,
# but write the UNFILTERED output to the log for debugging.
"$VENV_PY" 3dlegsim.py > >(tee "$LOGFILE") 2> >(tee -a "$LOGFILE" >&2) \
  | grep -Ev "cfurlcopyresourcepropertyforkey|kCFURL.*no scheme" || true

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
