"""
mock_cv.py — Simulates ESP32-CAM presence events without hardware.
Run this in a second terminal when testing without the camera.

Usage:
  python mock_cv.py

Commands (type and press Enter):
  p  → present       (you are at the desk, looking at screen)
  a  → absent        (you left the desk)
  d  → distracted    (you looked away)
  r  → returned      (you came back after absence)
  q  → quit

Also loops an automatic scenario for demo purposes if run with --demo flag.
"""

import sys
import time
import random
import threading
import requests

BASE = "http://localhost:8000"

def post_event(event_type: str):
    try:
        r = requests.post(f"{BASE}/cv/mock", json={"event": event_type}, timeout=2)
        print(f"  → Sent: {event_type}  (status {r.status_code})")
    except Exception as e:
        print(f"  → Error: {e} (is the server running?)")


def demo_loop():
    """Auto-demo: cycles through realistic presence patterns."""
    scenarios = [
        ("present",    15, "Working at desk..."),
        ("distracted", 8,  "Looking away from screen..."),
        ("present",    20, "Back to focus..."),
        ("absent",     12, "Left the desk..."),
        ("returned",   1,  "Returned to desk!"),
        ("present",    25, "Focused session..."),
        ("distracted", 5,  "Distracted again..."),
    ]
    print("\n[DEMO MODE] Cycling through presence scenarios. Ctrl+C to stop.\n")
    while True:
        for event, duration, label in scenarios:
            print(f"  [{event.upper()}] {label} (for {duration}s)")
            post_event(event)
            time.sleep(duration)


def manual_mode():
    print("\n=== Mock CV Controller ===")
    print("Commands: p=present  a=absent  d=distracted  r=returned  q=quit")
    print("Make sure the server is running at", BASE)
    print()
    while True:
        try:
            cmd = input("Event > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        mapping = {"p": "present", "a": "absent", "d": "distracted", "r": "returned"}
        if cmd == "q":
            break
        elif cmd in mapping:
            post_event(mapping[cmd])
        elif cmd in mapping.values():
            post_event(cmd)
        else:
            print("  Unknown command. Use: p, a, d, r, q")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo_loop()
    else:
        manual_mode()
