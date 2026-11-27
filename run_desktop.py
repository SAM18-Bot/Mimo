#!/usr/bin/env python3
"""Launch the Mimo Windows desktop app with `python run_desktop.py`.

The client connects to its configured HTTPS origin. Set MIMO_CLOUD_URL=local
to start the bundled FastAPI server. See docs/clients.md for setup and builds.
"""

import os
import sys

# Ensure the project root is always on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from desktop.main_desktop import main

if __name__ == "__main__":
    main()
