#!/usr/bin/env python3
"""
Mimo — Server-only Launcher
────────────────────────────
Starts Mimo as a plain background server.
Dashboard opens in your browser at http://localhost:8000.

Use this when:
  • You don't want the system tray icon
  • You're running Mimo on a remote / headless machine
  • You want hot-reload during development

For the full desktop experience (tray icon + native window):
  python run_desktop.py

Usage:
  python run_server.py              # production mode
  python run_server.py --dev        # hot-reload (file changes restart server)
  python run_server.py --port 8080  # custom port
"""

import argparse
import os
import sys
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description="Start the Mimo backend server.")
    parser.add_argument("--port", type=int, default=8000,    help="Port to listen on (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--dev",  action="store_true",        help="Enable hot-reload (development mode)")
    parser.add_argument("--no-browser", action="store_true",  help="Don't open browser automatically")
    args = parser.parse_args()

    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    print()
    print("  🔥  Mimo AI Accountability System")
    print("  ──────────────────────────────────")
    print(f"  Dashboard  → http://localhost:{args.port}")
    print(f"  API docs   → http://localhost:{args.port}/docs")
    print(f"  Settings   → http://localhost:{args.port}/settings")
    print(f"  Mode       → {'development (hot-reload)' if args.dev else 'production'}")
    print()
    print("  Press Ctrl+C to stop.")
    print()

    if not args.no_browser and not args.dev:
        # Open browser after a short delay (server needs a moment to start)
        import threading, time
        def _open():
            time.sleep(2.5)
            webbrowser.open(f"http://localhost:{args.port}")
        threading.Thread(target=_open, daemon=True).start()

    import uvicorn
    uvicorn.run(
        "main:app",
        host   = args.host,
        port   = args.port,
        reload = args.dev,
        log_level = "info",
    )


if __name__ == "__main__":
    main()
