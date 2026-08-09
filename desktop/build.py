import os
import subprocess
import sys

def build_executable():
    """Build the standalone Desktop Mimo App using PyInstaller."""
    
    print("Building Mimo Desktop Client executable...")
    
    # Run PyInstaller
    subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "-y",
        "--noconsole",
        "--name", "Mimo",
        # FastAPI / Uvicorn hidden imports
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "uvicorn.lifespan.off",
        "--hidden-import", "websockets",
        # Core hidden imports
        "--hidden-import", "psutil",
        "--hidden-import", "sqlite3",
        "--hidden-import", "pydantic",
        # Include static and assets directories
        "--add-data", f"static{os.pathsep}static",
        "--add-data", f"desktop/assets{os.pathsep}desktop/assets",
        "--icon", "desktop/assets/app_icon.ico",
        "run_desktop.py"
    ], check=True)
    
    print("Build complete! Executable is in the 'dist/Mimo' folder.")

if __name__ == "__main__":
    build_executable()
