"""
Unit tests for modules/screen_tracker/categorizer.py

Tests app categorization with:
  - Direct app name matches
  - Browser title pass-through
  - Unknown apps (should be neutral)
  - Edge cases (empty strings, mixed case)
"""

import pytest
from modules.screen_tracker.categorizer import categorize_app, is_browser


class TestProductiveApps:

    def test_vscode(self):
        assert categorize_app("code", "main.py") == "productive"

    def test_pycharm(self):
        assert categorize_app("pycharm", "project") == "productive"

    def test_terminal(self):
        assert categorize_app("terminal", "") == "productive"

    def test_jupyter(self):
        assert categorize_app("jupyter", "Notebook") == "productive"

    def test_chrome_with_github(self):
        assert categorize_app("chrome", "GitHub - Pull Request") == "productive"

    def test_chrome_with_stackoverflow(self):
        assert categorize_app("chrome", "Stack Overflow - How to sort") == "productive"

    def test_chrome_with_educational_youtube(self):
        assert categorize_app("chrome", "YouTube - Python tutorial for beginners") == "productive"

    def test_chrome_with_exam_youtube(self):
        assert categorize_app("chrome", "YouTube - Physics exam revision lecture") == "productive"

    def test_notion(self):
        assert categorize_app("notion", "Study Notes") == "productive"

    def test_vim(self):
        assert categorize_app("vim", "algorithm.py") == "productive"

    def test_zoom(self):
        assert categorize_app("zoom", "Study Group Meeting") == "productive"


class TestDistractingApps:

    def test_instagram(self):
        assert categorize_app("instagram", "") == "distracting"

    def test_youtube_in_title(self):
        assert categorize_app("chrome", "YouTube - Lo-fi music") == "distracting"

    def test_youtube_shorts_in_title(self):
        assert categorize_app("chrome", "YouTube Shorts - trending clips") == "distracting"

    def test_netflix(self):
        assert categorize_app("netflix", "") == "distracting"

    def test_reddit(self):
        assert categorize_app("chrome", "Reddit - r/memes") == "distracting"

    def test_tiktok(self):
        assert categorize_app("chrome", "TikTok - trending") == "distracting"

    def test_steam(self):
        assert categorize_app("steam", "Game Library") == "distracting"

    def test_facebook(self):
        assert categorize_app("facebook", "") == "distracting"


class TestNeutralApps:

    def test_unknown_app(self):
        assert categorize_app("unknownapp_xyz", "") == "neutral"

    def test_calculator(self):
        assert categorize_app("calculator", "") == "neutral"

    def test_file_manager(self):
        assert categorize_app("explorer", "") == "neutral"

    def test_settings(self):
        assert categorize_app("settings", "") == "neutral"


class TestEdgeCases:

    def test_empty_app_name(self):
        result = categorize_app("", "")
        assert result in ("productive", "neutral", "distracting")

    def test_uppercase_app(self):
        # Should handle case insensitively
        assert categorize_app("INSTAGRAM", "") == "distracting"
        assert categorize_app("CODE", "") == "productive"

    def test_distracting_wins_over_productive_in_title(self):
        # Browser title with instagram should be distracting, not productive
        result = categorize_app("chrome", "instagram.com - Best memes")
        assert result == "distracting"

    def test_partial_app_name_match(self):
        # "vscode" contains "code" → should match productive
        assert categorize_app("vscode", "") == "productive"


class TestIsBrowser:

    def test_chrome_is_browser(self):
        assert is_browser("chrome") is True

    def test_firefox_is_browser(self):
        assert is_browser("firefox") is True

    def test_brave_is_browser(self):
        assert is_browser("brave") is True

    def test_code_is_not_browser(self):
        assert is_browser("code") is False

    def test_instagram_is_not_browser(self):
        assert is_browser("instagram") is False
