#!/usr/bin/env python3
"""
Mimo Desktop App Launcher
─────────────────────────
Run this file to start Mimo as a desktop application.

Usage:
    python run_desktop.py

What it does:
  1. Starts the FastAPI server (background)
  2. Shows a loading splash screen
  3. Opens Mimo in a native window (via pywebview)
     OR in your default browser if pywebview isn't installed
  4. Adds a system tray icon for quick access
  5. App continues running in tray when you close the window

Requirements:
    pip install -r requirements.txt
    pip install -r requirements_desktop.txt
"""

import os
import sys

# Ensure the project root is always on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from desktop.main_desktop import main

if __name__ == "__main__":
    main()
