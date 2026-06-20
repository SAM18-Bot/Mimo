"""
mock_screen.py — Interactive screen-event injector for testing without real OS hooks.

Mirrors mock_cv.py but for window/app changes.

Usage:
  python mock_screen.py            ← interactive mode
  python mock_screen.py --demo     ← auto-demo cycle (good for hackathon judges)
  python mock_screen.py --rapid    ← rapid fire of typical study-day events

Commands (interactive mode):
  c  → VS Code (productive)
  n  → Notion  (productive)
  g  → GitHub  (productive)
  i  → Instagram (distracting)
  y  → YouTube   (distracting)
  r  → Reddit    (distracting)
  e  → Explorer  (neutral)
  s  → Spotify   (neutral)
  ?  → custom    (enter app + title manually)
  q  → quit
"""

import sys
import time
import requests

BASE = "http://localhost:8000"

PRESETS = {
    "c": ("code",      "main.py — Mimo [active]",       ""),
    "n": ("notion",    "Study Notes — Today's Plan",          ""),
    "g": ("chrome",    "GitHub — Pull Request Review",        "productive"),
    "i": ("chrome",    "Instagram — Home Feed",               "distracting"),
    "y": ("chrome",    "YouTube — Lo-fi Beats to Study",      "distracting"),
    "r": ("chrome",    "Reddit — r/ProgrammerHumor",          "distracting"),
    "e": ("explorer",  "Downloads",                           "neutral"),
    "s": ("spotify",   "Lofi Girl — Study beats",            "neutral"),
}

LABEL = {
    "c": "VS Code      [productive]",
    "n": "Notion       [productive]",
    "g": "GitHub       [productive]",
    "i": "Instagram    [distracting]",
    "y": "YouTube      [distracting]",
    "r": "Reddit       [distracting]",
    "e": "Explorer     [neutral]",
    "s": "Spotify      [neutral]",
}


def post_window(app: str, title: str, category: str = ""):
    payload = {"app": app, "title": title}
    if category:
        payload["category"] = category
    try:
        r = requests.post(f"{BASE}/screen/mock", json=payload, timeout=2)
        cat = r.json().get("category", "?")
        print(f"  → {app:12} | {cat:11} | {title[:45]}")
    except Exception as e:
        print(f"  → Error: {e}  (is the server running on port 8000?)")


def demo_loop():
    """
    Auto-demo: realistic study-day simulation.
    Great for showing judges a live working system.
    """
    SCENARIO = [
        ("code",      "ai_project.py — Mimo",           "", 20,  "Opening VS Code..."),
        ("chrome",    "Stack Overflow — Python FastAPI WebSocket", "", 15, "Researching..."),
        ("code",      "dashboard.html — Mimo",          "", 25,  "Back to coding..."),
        ("chrome",    "Instagram — Home Feed",               "distracting", 12, "💀 Opened Instagram"),
        ("chrome",    "YouTube — Big Buck Bunny",            "distracting", 8,  "💀 YouTube now"),
        ("code",      "main.py — Mimo",                 "", 20,  "Back to work..."),
        ("notion",    "Study Notes — Algorithm Revision",    "", 15,  "Taking notes..."),
        ("chrome",    "Reddit — r/learnpython",              "distracting", 5,  "💀 Reddit again"),
        ("code",      "test_api.py — Mimo",             "", 30,  "Writing tests..."),
    ]

    print("\n[DEMO MODE] Running realistic study-day simulation. Ctrl+C to stop.\n")
    while True:
        for app, title, cat, duration, label in SCENARIO:
            print(f"\n  [{label}] {duration}s")
            post_window(app, title, cat)
            time.sleep(duration)


def rapid_fire():
    """
    Rapid sequence for testing roast engine trigger logic quickly.
    """
    events = [
        ("code",      "project.py",         "", 3),
        ("instagram", "Home Feed",          "distracting", 3),
        ("code",      "project.py",         "", 3),
        ("chrome",    "YouTube",            "distracting", 3),
        ("code",      "project.py",         "", 3),
        ("chrome",    "Reddit",             "distracting", 3),
    ]
    print("\n[RAPID] Firing events every 3 seconds...\n")
    for app, title, cat, delay in events:
        post_window(app, title, cat)
        time.sleep(delay)
    print("\nDone.")


def interactive():
    print("\n=== Mock Screen Controller ===")
    print(f"Connected to: {BASE}")
    print()
    print("  c = VS Code     n = Notion      g = GitHub")
    print("  i = Instagram   y = YouTube     r = Reddit")
    print("  e = Explorer    s = Spotify     ? = custom")
    print("  q = quit")
    print()

    while True:
        try:
            cmd = input("Window > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if cmd == "q":
            break
        elif cmd in PRESETS:
            app, title, cat = PRESETS[cmd]
            post_window(app, title, cat)
        elif cmd == "?":
            try:
                app   = input("  App name: ").strip()
                title = input("  Window title: ").strip()
                post_window(app, title)
            except KeyboardInterrupt:
                continue
        else:
            print("  Unknown. Use: c n g i y r e s ? q")


if __name__ == "__main__":
    if "--demo"  in sys.argv:
        demo_loop()
    elif "--rapid" in sys.argv:
        rapid_fire()
    else:
        interactive()
