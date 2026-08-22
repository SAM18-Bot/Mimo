"""
Splash screen shown while the FastAPI server is starting up.
Uses tkinter (built into Python — no extra install needed).

Shows a dark-themed window with the Mimo name, a progress message,
and a simple animated dots indicator.

Usage:
    splash = SplashScreen()
    splash.show()               # non-blocking — runs in its own thread
    # ... wait for server ...
    splash.update("Almost ready...")
    splash.close()              # close and destroy
"""

import logging
import threading
import time

log = logging.getLogger(__name__)


class SplashScreen:
    def __init__(self):
        self._root     = None
        self._label    = None
        self._dots_lbl = None
        self._thread   = None
        self._running  = False
        self._msg      = "Starting server…"
        self._lock     = threading.Lock()

    def show(self):
        """Show the splash in a background thread (non-blocking)."""
        self._running = True
        self._thread  = threading.Thread(
            target=self._run_tk, daemon=True, name="splash"
        )
        self._thread.start()
        time.sleep(0.1)   # brief pause so window appears before caller continues

    def update(self, message: str):
        """Update the status message while the splash is visible."""
        with self._lock:
            self._msg = message
        if self._label:
            try:
                self._label.after(0, lambda: self._label.config(text=message))
            except Exception:
                pass

    def close(self):
        """Close and destroy the splash screen."""
        self._running = False
        if self._root:
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass

    def _run_tk(self):
        try:
            import tkinter as tk
            from tkinter import font as tkfont

            root = tk.Tk()
            self._root = root

            root.title("Mimo")
            root.overrideredirect(True)      # no OS chrome
            root.configure(bg="#07070f")
            root.attributes("-topmost", True)
            root.lift()

            # Size and center
            w, h = 380, 200
            sw   = root.winfo_screenwidth()
            sh   = root.winfo_screenheight()
            x    = (sw - w) // 2
            y    = (sh - h) // 2
            root.geometry(f"{w}x{h}+{x}+{y}")

            # Rounded-ish border (just a coloured frame)
            outer = tk.Frame(root, bg="#14142a", padx=2, pady=2)
            outer.pack(fill="both", expand=True)
            inner = tk.Frame(outer, bg="#07070f", padx=24, pady=24)
            inner.pack(fill="both", expand=True)

            # Flame + name
            tk.Label(
                inner, text="🔥  Mimo",
                font=("Segoe UI", 22, "bold"),
                fg="#e2e2f0", bg="#07070f",
            ).pack(anchor="w")

            tk.Label(
                inner, text="AI Accountability System",
                font=("Segoe UI", 11),
                fg="#5a5a7a", bg="#07070f",
            ).pack(anchor="w", pady=(4, 20))

            # Status label
            self._label = tk.Label(
                inner, text=self._msg,
                font=("Segoe UI", 11),
                fg="#7c6fe0", bg="#07070f",
            )
            self._label.pack(anchor="w")

            # Animated dots
            self._dots_lbl = tk.Label(
                inner, text="●  ●  ●",
                font=("Segoe UI", 10),
                fg="#14142a", bg="#07070f",
            )
            self._dots_lbl.pack(anchor="w", pady=(8, 0))

            # Start dot animation
            root.after(100, self._animate_dots)

            root.mainloop()

        except ImportError:
            log.debug("tkinter not available — skipping splash screen.")
        except Exception as e:
            log.debug("Splash screen error (non-critical): %s", e)

    _dot_states = ["●  ○  ○", "●  ●  ○", "●  ●  ●", "○  ●  ●", "○  ○  ●", "○  ○  ○"]
    _dot_idx    = 0

    def _animate_dots(self):
        if not self._running or not self._root:
            return
        try:
            dots_text = self._dot_states[self._dot_idx % len(self._dot_states)]
            self._dot_idx += 1
            if self._dots_lbl:
                self._dots_lbl.config(text=dots_text, fg="#7c6fe0")
            # Also sync message
            with self._lock:
                msg = self._msg
            if self._label:
                self._label.config(text=msg)
            self._root.after(400, self._animate_dots)
        except Exception:
            pass
