"""
Settings manager — reads from and writes to the .env file.

Usage:
    from desktop.settings_manager import load_settings, save_setting, get_setting

All sensitive keys (API keys) are masked when returned for display.
"""

import logging
import os
from typing import Any

from dotenv import dotenv_values, load_dotenv, set_key

log = logging.getLogger(__name__)

# Resolved path to the .env file in the project root
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_PATH = os.path.join(_ROOT, ".env")

# Keys that should be masked in the UI (show ••••)
_SENSITIVE_KEYS = {"GEMINI_API_KEY"}

# Default values for each setting
DEFAULTS: dict[str, Any] = {
    "GEMINI_API_KEY":                    "",
    "DATABASE_URL":                      "sqlite:///./accountability.db",
    "ESP32_STREAM_URL":                  "http://192.168.1.100:81/stream",
    "NO_HARDWARE":                       "1",
    "NO_VOICE":                          "1",
    "DISTRACTION_ROAST_AFTER_MINUTES":   "5",
    "ABSENCE_ROAST_AFTER_MINUTES":       "15",
    "MIN_ROAST_INTERVAL_SECONDS":        "300",
    "EOD_REPORT_HOUR":                   "22",
    "REMINDER_CHECK_INTERVAL_MINUTES":   "15",
    "LIVE_ROAST_USE_AI":                 "True",
}

# Human-readable labels for the settings UI
LABELS: dict[str, str] = {
    "GEMINI_API_KEY":                    "Gemini API Key",
    "DATABASE_URL":                      "Database URL",
    "ESP32_STREAM_URL":                  "ESP32-CAM Stream URL",
    "NO_HARDWARE":                       "Disable Camera (NO_HARDWARE)",
    "NO_VOICE":                          "Disable Voice (NO_VOICE)",
    "DISTRACTION_ROAST_AFTER_MINUTES":   "Minutes on distraction before roast",
    "ABSENCE_ROAST_AFTER_MINUTES":       "Minutes absent before roast",
    "MIN_ROAST_INTERVAL_SECONDS":        "Min seconds between roasts",
    "EOD_REPORT_HOUR":                   "End-of-day report hour (0–23)",
    "REMINDER_CHECK_INTERVAL_MINUTES":   "Reminder check interval (minutes)",
    "LIVE_ROAST_USE_AI":                 "Use AI for roasts (else pre-written)",
}

SECTIONS: dict[str, list[str]] = {
    "AI": ["GEMINI_API_KEY", "LIVE_ROAST_USE_AI"],
    "Hardware": ["NO_HARDWARE", "ESP32_STREAM_URL"],
    "Voice": ["NO_VOICE"],
    "Behavior Thresholds": [
        "DISTRACTION_ROAST_AFTER_MINUTES",
        "ABSENCE_ROAST_AFTER_MINUTES",
        "MIN_ROAST_INTERVAL_SECONDS",
    ],
    "Schedule": ["EOD_REPORT_HOUR", "REMINDER_CHECK_INTERVAL_MINUTES"],
    "Advanced": ["DATABASE_URL"],
}


def load_settings(mask_sensitive: bool = True) -> dict:
    """
    Load all settings from the .env file.
    Sensitive keys are masked with '••••••••' when mask_sensitive=True.
    Returns dict of {key: value}.
    """
    # Read raw values
    raw = dotenv_values(_ENV_PATH) if os.path.exists(_ENV_PATH) else {}

    result = {}
    for key, default in DEFAULTS.items():
        value = raw.get(key, default) or default

        if mask_sensitive and key in _SENSITIVE_KEYS and value:
            # Show first 8 chars then ••••••••
            display = value[:8] + "••••••••" if len(value) > 8 else "••••••••"
            result[key] = display
        else:
            result[key] = value

    return result


def get_setting(key: str) -> str | None:
    """Get a single raw setting value."""
    raw = dotenv_values(_ENV_PATH) if os.path.exists(_ENV_PATH) else {}
    return raw.get(key, DEFAULTS.get(key, ""))


def save_setting(key: str, value: str) -> bool:
    """
    Write a single setting to the .env file.
    Creates the file if it doesn't exist.
    Returns True on success.
    """
    if key not in DEFAULTS:
        log.warning("Unknown setting key: %s", key)
        return False

    # Don't save masked values
    if value and "••••" in value:
        log.debug("Skipping masked value for %s", key)
        return True

    try:
        # Ensure .env file exists
        if not os.path.exists(_ENV_PATH):
            with open(_ENV_PATH, "w") as f:
                f.write("")

        set_key(_ENV_PATH, key, value)
        load_dotenv(_ENV_PATH, override=True)   # reload into os.environ immediately
        log.info("Setting saved: %s = %s", key, "••••" if key in _SENSITIVE_KEYS else value)
        return True

    except Exception as e:
        log.error("Failed to save setting %s: %s", key, e)
        return False


def save_many(settings: dict) -> dict:
    """
    Save multiple settings at once.
    Returns dict of {key: success_bool}.
    """
    results = {}
    for key, value in settings.items():
        results[key] = save_setting(key, str(value))

    # Reload config module so changes take effect without restart
    _reload_config()
    return results


def _reload_config():
    """Reload the project config module so new .env values take effect."""
    try:
        import importlib

        import config
        load_dotenv(_ENV_PATH, override=True)
        importlib.reload(config)
        log.info("Config reloaded successfully.")
    except Exception as e:
        log.warning("Config reload failed (restart may be needed): %s", e)


def get_settings_for_ui() -> dict:
    """
    Returns settings grouped by section, with labels.
    Used by the settings HTML page.
    """
    raw_values = load_settings(mask_sensitive=True)

    sections = []
    for section_name, keys in SECTIONS.items():
        items = []
        for key in keys:
            items.append({
                "key":       key,
                "label":     LABELS.get(key, key),
                "value":     raw_values.get(key, ""),
                "sensitive": key in _SENSITIVE_KEYS,
                "type":      _infer_input_type(key),
            })
        sections.append({"name": section_name, "items": items})

    return {"sections": sections}


def _infer_input_type(key: str) -> str:
    """Determine the HTML input type for a setting key."""
    if key in _SENSITIVE_KEYS:
        return "password"
    if key in ("NO_HARDWARE", "NO_VOICE", "LIVE_ROAST_USE_AI"):
        return "toggle"
    if key in ("EOD_REPORT_HOUR", "DISTRACTION_ROAST_AFTER_MINUTES",
               "ABSENCE_ROAST_AFTER_MINUTES", "MIN_ROAST_INTERVAL_SECONDS",
               "REMINDER_CHECK_INTERVAL_MINUTES"):
        return "number"
    return "text"
