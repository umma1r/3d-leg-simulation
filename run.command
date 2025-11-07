```bash
#!/bin/bash
# macOS auto-launch script for 3D Leg Simulation
# Double-clickable in Finder

echo "=== 3D Leg Simulation Setup and Launch (macOS) ==="
echo ""

# Check for Python 3
if ! command -v python3 &>/dev/null; then
  echo "Python 3 not found. Installing via Homebrew..."
  if ! command -v brew &>/dev/null; then
    echo "Homebrew not found. Installing Homebrew first..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  fi
  brew install python@3.11
fi

PYTHON=$(command -v python3)
echo "Using Python: $PYTHON"

# Create virtual environment if missing
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  "$PYTHON" -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Upgrade pip and install requirements
echo "Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# Run the desktop simulation
echo "Starting Leg Simulation..."
python 3dlegsim.py

echo ""
echo "Simulation closed. You may quit Terminal."
