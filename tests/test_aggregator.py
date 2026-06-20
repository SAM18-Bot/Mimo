"""
Integration tests for modules/behavior_engine/aggregator.py

Tests:
  - Daily stats computation from seeded DB data
  - Focus score calculation
  - Top app aggregation
  - Longest focus stretch
  - Peak hour detection
  - Assignment status in stats
"""

import pytest
from datetime import date, datetime, timedelta
from modules.behavior_engine.aggregator import (
    get_daily_stats, save_daily_summary, _compute_focus_score,
    _top_apps, _longest_consecutive_productive,
)
from db.models import ScreenSession, DailySummary


class TestDailyStats:

    def test_empty_day_returns_zeros(self, db_session):
        stats = get_daily_stats(db_session)
        assert stats["productive_min"]  == 0
        assert stats["distracting_min"] == 0
        assert stats["focus_score"]     == 0.0
        assert stats["distraction_count"] == 0

    def test_productive_time_aggregated(self, db_session, seed_sessions):
        seed_sessions([
            {"app": "code",  "category": "productive", "duration": 3600},  # 60m
            {"app": "code",  "category": "productive", "duration": 1800},  # 30m
        ])
        stats = get_daily_stats(db_session)
        assert stats["productive_min"] == 90

    def test_distracting_time_aggregated(self, db_session, seed_sessions):
        seed_sessions([
            {"app": "instagram", "category": "distracting", "duration": 900},   # 15m
            {"app": "youtube",   "category": "distracting", "duration": 1800},  # 30m
        ])
        stats = get_daily_stats(db_session)
        assert stats["distracting_min"] == 45

    def test_mixed_sessions_correct_totals(self, db_session, seed_sessions):
        seed_sessions([
            {"app": "code",      "category": "productive",  "duration": 3600},
            {"app": "instagram", "category": "distracting", "duration": 600},
            {"app": "explorer",  "category": "neutral",     "duration": 300},
        ])
        stats = get_daily_stats(db_session)
        assert stats["productive_min"]  == 60
        assert stats["distracting_min"] == 10
        assert stats["neutral_min"]     == 5

    def test_top_productive_apps(self, db_session, seed_sessions):
        seed_sessions([
            {"app": "code",   "category": "productive", "duration": 3600},
            {"app": "notion", "category": "productive", "duration": 1800},
        ])
        stats = get_daily_stats(db_session)
        assert "code" in stats["productive_apps"]
        assert "60m"  in stats["productive_apps"]

    def test_top_distracting_apps(self, db_session, seed_sessions):
        seed_sessions([
            {"app": "instagram", "category": "distracting", "duration": 900},
        ])
        stats = get_daily_stats(db_session)
        assert "instagram" in stats["distracting_apps"]

    def test_no_sessions_today_excludes_other_dates(self, db_session, seed_sessions):
        yesterday = date.today() - timedelta(days=1)
        seed_sessions([
            {"app": "code", "category": "productive", "duration": 3600,
             "date": yesterday,
             "started": datetime.combine(yesterday, datetime.min.time()),
             "ended":   datetime.combine(yesterday, datetime.min.time()) + timedelta(hours=1)},
        ])
        stats = get_daily_stats(db_session, target_date=date.today())
        assert stats["productive_min"] == 0   # yesterday's data should not appear

    def test_longest_focus_detected(self, db_session, seed_sessions):
        now = datetime.now()
        seed_sessions([
            {"app": "code", "category": "productive", "duration": 7200,
             "started": now - timedelta(hours=3), "ended": now - timedelta(hours=1)},
            {"app": "code", "category": "productive", "duration": 1800,
             "started": now - timedelta(hours=1), "ended": now - timedelta(minutes=30)},
        ])
        stats = get_daily_stats(db_session)
        assert stats["longest_focus_min"] == 120  # 7200 // 60

    def test_peak_hour_detected(self, db_session, seed_sessions):
        now = datetime.now()
        # Most productive time at 9am
        morning_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
        seed_sessions([
            {"app": "code", "category": "productive", "duration": 5400,
             "started": morning_start, "ended": morning_start + timedelta(hours=1.5)},
        ])
        stats = get_daily_stats(db_session)
        assert stats["peak_hour"] == 9

    def test_upcoming_assignments_in_stats(self, db_session, seed_assignments):
        seed_assignments([
            {"title": "Math HW",    "due_date": date.today() + timedelta(days=2)},
            {"title": "Physics Lab", "due_date": date.today() + timedelta(days=5)},
        ])
        stats = get_daily_stats(db_session)
        titles = " ".join(stats["upcoming_list"])
        assert "Math HW" in titles

    def test_overdue_in_stats(self, db_session, seed_assignments):
        seed_assignments([
            {"title": "Late Essay", "due_date": date.today() - timedelta(days=3), "status": "pending"},
        ])
        stats = get_daily_stats(db_session)
        overdue_text = " ".join(stats["overdue_list"])
        assert "Late Essay" in overdue_text

    def test_done_assignments_not_in_overdue(self, db_session, seed_assignments):
        seed_assignments([
            {"title": "Done Stuff", "due_date": date.today() - timedelta(days=1), "status": "done"},
        ])
        stats = get_daily_stats(db_session)
        assert stats["overdue_list"] == []


class TestFocusScore:

    def test_all_productive_high_score(self):
        score = _compute_focus_score(
            productive_s=7200, total_screen_s=7200, distraction_count=0
        )
        assert score > 90

    def test_all_distracting_low_score(self):
        score = _compute_focus_score(
            productive_s=0, total_screen_s=7200, distraction_count=10
        )
        assert score < 10

    def test_zero_screen_time(self):
        score = _compute_focus_score(
            productive_s=0, total_screen_s=0, distraction_count=0
        )
        assert score == 0.0

    def test_score_between_zero_and_hundred(self):
        for prod, total, dist in [
            (1800, 3600, 3),
            (3600, 3600, 0),
            (0, 3600, 15),
            (900, 3600, 8),
        ]:
            score = _compute_focus_score(prod, total, dist)
            assert 0.0 <= score <= 100.0, f"Out of range: {score} for {prod}/{total}/{dist}"


class TestSaveDailySummary:

    def test_save_creates_row(self, db_session, seed_sessions):
        seed_sessions([
            {"app": "code", "category": "productive", "duration": 3600},
        ])
        stats = get_daily_stats(db_session)
        save_daily_summary(db_session, stats)

        row = db_session.query(DailySummary).filter(
            DailySummary.date == date.today()
        ).first()
        assert row is not None
        assert row.productive_time_s == 3600

    def test_save_upserts_existing_row(self, db_session, seed_sessions):
        """Calling save twice should update the row, not create a duplicate."""
        seed_sessions([{"app": "code", "category": "productive", "duration": 1800}])
        stats = get_daily_stats(db_session)
        save_daily_summary(db_session, stats)
        save_daily_summary(db_session, stats)

        count = db_session.query(DailySummary).filter(
            DailySummary.date == date.today()
        ).count()
        assert count == 1
