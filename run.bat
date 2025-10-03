@echo off
REM Create venv if missing
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install "PyQt5==5.15.*" "vtk>=9.2,<10"
python 3dlegsim.py
