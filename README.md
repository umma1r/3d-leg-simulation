# 3D Leg Simulation — How to Run

## macOS

### Quick start (no terminal commands needed)

1. **Download ZIP**  
   Go to the GitHub page → click **Code → Download ZIP** and extract the folder.

2. **Run the app**  
   Inside the unzipped folder, **double-click** the file named **`run.command`**.  
   macOS will open Terminal, automatically:
   - check or install Python 3 (via Homebrew if missing),  
   - create a virtual environment,  
   - install required packages, and  
   - launch the simulation (`3dlegsim.py`).

   The first run may take a few minutes if Python or libraries need to be installed.

3. If macOS shows a security prompt (“cannot be opened because it is from an unidentified developer”),  
   right-click `run.command` → **Open** → then choose **Open** again.
   
 Leg Force Simulation (trame + vtk-osmesa) IN PROGRESS

**How to run on Binder**
1. Click the Binder badge below.
2. When JupyterLab opens, **File → New → Terminal**.
3. Run: `python main.py`
4. Open `/proxy/8000/` in the same tab (or copy that path into the address bar).

Binder badge (replace with your repo path):
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/YOUR_GH_USER/leg-sim-trame/HEAD?urlpath=lab)
