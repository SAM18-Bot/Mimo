"""
Categorizes an app_name string as productive | distracting | neutral.
Logic: keyword matching against config lists.
Browser titles get a secondary pass — 'youtube' in a chrome title = distracting.
"""

import config


def categorize_app(app_name: str, window_title: str = "") -> str:
    app_lower   = (app_name or "").lower()
    title_lower = (window_title or "").lower()

    if "youtube" in app_lower or "youtube" in title_lower:
        if any(kw in title_lower for kw in config.YOUTUBE_EDUCATIONAL_KEYWORDS):
            return "productive"
        if any(kw in title_lower for kw in config.YOUTUBE_DISTRACTING_KEYWORDS):
            return "distracting"
        return "distracting"

    # Check distracting first (higher priority — a browser showing Instagram is distracting)
    for kw in config.DISTRACTING_KEYWORDS:
        if kw in app_lower or kw in title_lower:
            return "distracting"

    for kw in config.PRODUCTIVE_KEYWORDS:
        if kw in app_lower or kw in title_lower:
            return "productive"

    for kw in config.NEUTRAL_KEYWORDS:
        if kw in app_lower or kw in title_lower:
            return "neutral"

    return "neutral"   # default — unknown apps don't penalize score


def is_browser(app_name: str) -> bool:
    browsers = {"chrome", "chromium", "firefox", "edge", "brave", "safari", "opera"}
    return any(b in app_name.lower() for b in browsers)
