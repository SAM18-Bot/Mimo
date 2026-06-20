"""
Unit tests for modules/screen_tracker/session.py (SessionStitcher + analyze_sessions).
"""

import pytest
from datetime import datetime, timedelta
from modules.screen_tracker.session import SessionStitcher, Session, analyze_sessions


@pytest.fixture
def stitcher():
    return SessionStitcher(gap_threshold_s=10)


def t(minutes_ago: float) -> datetime:
    """Return a datetime N minutes ago."""
    return datetime.now() - timedelta(minutes=minutes_ago)


class TestSessionStitcher:

    def test_first_event_no_return(self, stitcher):
        result = stitcher.on_window_change("code", "main.py", "productive", t(10))
        assert result is None   # no completed session yet

    def test_window_change_closes_session(self, stitcher):
        stitcher.on_window_change("code",      "main.py",   "productive", t(5))
        closed = stitcher.on_window_change("instagram", "Home",     "distracting", t(1))
        assert closed is not None
        assert closed.app == "code"
        assert closed.category == "productive"

    def test_session_duration_correct(self, stitcher):
        start = t(2)
        end   = t(0)
        stitcher.on_window_change("code", "", "productive", start)
        # Change to another app 2 minutes later
        closed = stitcher.on_window_change("chrome", "", "neutral", end)
        assert closed is not None
        # Duration should be ~120 seconds (2 minutes)
        assert 100 <= closed.duration_s <= 140

    def test_same_app_updates_title(self, stitcher):
        stitcher.on_window_change("code", "file_a.py", "productive", t(5))
        result = stitcher.on_window_change("code", "file_b.py", "productive", t(3))
        # Same app — no session closed
        assert result is None
        # Title should be updated
        assert stitcher.get_pending().title == "file_b.py"

    def test_flush_closes_pending(self, stitcher):
        stitcher.on_window_change("code", "main.py", "productive", t(5))
        closed = stitcher.flush()
        assert closed is not None
        assert closed.app == "code"

    def test_flush_empty_returns_none(self, stitcher):
        assert stitcher.flush() is None

    def test_multiple_sessions_tracked(self, stitcher):
        stitcher.on_window_change("code",      "", "productive",  t(10))
        stitcher.on_window_change("instagram", "", "distracting", t(7))
        stitcher.on_window_change("notion",    "", "productive",  t(4))
        stitcher.flush()

        completed = stitcher.get_completed()
        assert len(completed) == 3

    def test_reset_clears_state(self, stitcher):
        stitcher.on_window_change("code", "", "productive", t(5))
        stitcher.reset()
        assert stitcher.get_pending()    is None
        assert stitcher.get_completed() == []

    def test_gap_threshold_between_different_apps(self, stitcher):
        # Within gap: code → chrome (4s) → code should NOT absorb gap
        # (gap absorption only works for returning to same app)
        stitcher.on_window_change("code",   "", "productive", t(5))
        stitcher.on_window_change("chrome", "", "neutral",    t(4))
        completed = stitcher.get_completed()
        # code session should be closed
        assert len(completed) == 1
        assert completed[0].app == "code"


class TestSessionQualityScore:

    def test_long_productive_session_high_score(self):
        s = Session("code", "", "productive", datetime.now() - timedelta(hours=2))
        s.close(datetime.now())
        assert s.quality_score() >= 100.0  # capped at 100

    def test_short_distracting_high_score(self):
        """A 1-minute distraction is less harmful → higher score."""
        s = Session("instagram", "", "distracting", datetime.now() - timedelta(minutes=1))
        s.close(datetime.now())
        assert s.quality_score() >= 90

    def test_long_distracting_low_score(self):
        """A 15-minute distraction → low score."""
        s = Session("instagram", "", "distracting", datetime.now() - timedelta(minutes=15))
        s.close(datetime.now())
        assert s.quality_score() <= 10

    def test_neutral_is_50(self):
        s = Session("explorer", "", "neutral", datetime.now() - timedelta(minutes=5))
        s.close(datetime.now())
        assert s.quality_score() == 50.0


class TestAnalyzeSessions:

    def _make_session(self, app, cat, duration_s):
        now = datetime.now()
        s   = Session(app, "", cat, now - timedelta(seconds=duration_s))
        s.close(now)
        return s

    def test_empty_sessions(self):
        result = analyze_sessions([])
        assert result["longest_focus_min"]        == 0
        assert result["productive_session_count"] == 0
        assert result["total_sessions"]           == 0

    def test_longest_focus_detected(self):
        sessions = [
            self._make_session("code",   "productive",  3600),  # 60 min
            self._make_session("notion", "productive",  1800),  # 30 min
        ]
        result = analyze_sessions(sessions)
        assert result["longest_focus_min"] == 60

    def test_productive_session_count(self):
        sessions = [
            self._make_session("code",      "productive",  1800),
            self._make_session("instagram", "distracting", 600),
            self._make_session("notion",    "productive",  900),
        ]
        result = analyze_sessions(sessions)
        assert result["productive_session_count"] == 2

    def test_total_sessions_count(self):
        sessions = [
            self._make_session("code",      "productive",  1000),
            self._make_session("instagram", "distracting", 500),
        ]
        result = analyze_sessions(sessions)
        assert result["total_sessions"] == 2

    def test_avg_quality_score_present(self):
        sessions = [
            self._make_session("code", "productive", 3600),
        ]
        result = analyze_sessions(sessions)
        assert result["avg_session_quality"] > 0
