"""
Unit tests for modules/behavior_engine/scorer.py

Tests:
  - Score formula correctness
  - Letter grade thresholds
  - Edge cases (zero time, 100% productive, etc.)
  - Streak calculation
  - Percentile calculation
"""

import pytest
from modules.behavior_engine.scorer import ProductivityScorer, score_day


@pytest.fixture
def scorer():
    return ProductivityScorer()


class TestScoreFormula:

    def test_perfect_day(self, scorer):
        """8h productive, always present, no distractions, 2h focus block."""
        result = scorer.compute(
            productive_s      = 8 * 3600,
            total_screen_s    = 8 * 3600,
            present_events    = 20,
            total_cv_events   = 20,
            distraction_count = 0,
            longest_focus_s   = 7200,
        )
        assert result.final_score >= 90
        assert result.letter_grade == "A"
        assert result.focus_bonus  == 10.0

    def test_terrible_day(self, scorer):
        """All distracting, never present, frequent switches."""
        result = scorer.compute(
            productive_s      = 0,
            total_screen_s    = 4 * 3600,
            present_events    = 2,
            total_cv_events   = 20,
            distraction_count = 15,
            longest_focus_s   = 0,
        )
        assert result.final_score < 20
        assert result.letter_grade == "F"

    def test_mediocre_day(self, scorer):
        """Half productive, some presence issues, moderate distractions."""
        result = scorer.compute(
            productive_s      = 2 * 3600,
            total_screen_s    = 4 * 3600,
            present_events    = 12,
            total_cv_events   = 20,
            distraction_count = 5,
            longest_focus_s   = 1800,
        )
        assert 35 <= result.final_score <= 75

    def test_no_screen_time(self, scorer):
        """Zero time tracked → score should be 0."""
        result = scorer.compute(
            productive_s=0, total_screen_s=0,
            present_events=0, total_cv_events=0,
            distraction_count=0, longest_focus_s=0,
        )
        assert result.final_score == 0.0

    def test_score_clamped_to_100(self, scorer):
        """Score should never exceed 100."""
        result = scorer.compute(
            productive_s=9999999, total_screen_s=10000000,
            present_events=100, total_cv_events=100,
            distraction_count=0, longest_focus_s=99999,
        )
        assert result.final_score <= 100.0

    def test_score_clamped_to_0(self, scorer):
        """Score should never go below 0."""
        result = scorer.compute(
            productive_s=0, total_screen_s=100,
            present_events=0, total_cv_events=100,
            distraction_count=50, longest_focus_s=0,
        )
        assert result.final_score >= 0.0

    def test_long_focus_bonus_applied(self, scorer):
        """60+ minutes of focus gives +10 bonus."""
        without = scorer.compute(
            productive_s=3600, total_screen_s=3600,
            present_events=10, total_cv_events=10,
            distraction_count=0, longest_focus_s=1800,   # 30 min — no bonus
        )
        with_bonus = scorer.compute(
            productive_s=3600, total_screen_s=3600,
            present_events=10, total_cv_events=10,
            distraction_count=0, longest_focus_s=3600,   # 60 min — bonus
        )
        assert with_bonus.focus_bonus == 10.0
        assert without.focus_bonus    == 0.0
        assert with_bonus.final_score > without.final_score

    def test_switch_penalty_capped(self, scorer):
        """Penalty should not exceed MAX_SWITCH_PENALTY."""
        result = scorer.compute(
            productive_s=3600, total_screen_s=3600,
            present_events=10, total_cv_events=10,
            distraction_count=100,    # huge number
            longest_focus_s=0,
        )
        assert result.switch_penalty >= -scorer.MAX_SWITCH_PENALTY


class TestLetterGrades:

    def test_grade_a(self, scorer):
        assert scorer.letter_grade(90) == "A"
        assert scorer.letter_grade(85) == "A"

    def test_grade_b(self, scorer):
        assert scorer.letter_grade(75) == "B"
        assert scorer.letter_grade(70) == "B"

    def test_grade_c(self, scorer):
        assert scorer.letter_grade(60) == "C"
        assert scorer.letter_grade(50) == "C"

    def test_grade_d(self, scorer):
        assert scorer.letter_grade(40) == "D"
        assert scorer.letter_grade(35) == "D"

    def test_grade_f(self, scorer):
        assert scorer.letter_grade(34) == "F"
        assert scorer.letter_grade(0)  == "F"

    def test_boundary_85(self, scorer):
        assert scorer.letter_grade(84.9) == "B"
        assert scorer.letter_grade(85.0) == "A"


class TestSimpleScore:

    def test_simple_score_basic(self, scorer):
        s = scorer.simple_score(
            productive_s=3600, total_screen_s=7200, distraction_count=2
        )
        assert 0 <= s <= 100

    def test_simple_score_zero_total(self, scorer):
        s = scorer.simple_score(productive_s=0, total_screen_s=0, distraction_count=0)
        assert s == 0.0


class TestStreak:

    def test_streak_three_days(self, scorer):
        scores = [80, 75, 60, 20]   # 3 good days then a bad one
        assert scorer.compute_streak(scores, threshold=50) == 3

    def test_streak_broken_immediately(self, scorer):
        scores = [30, 80, 80]
        assert scorer.compute_streak(scores, threshold=50) == 0

    def test_empty_history(self, scorer):
        assert scorer.compute_streak([], threshold=50) == 0

    def test_all_good(self, scorer):
        scores = [70, 75, 80, 65, 90]
        assert scorer.compute_streak(scores, threshold=50) == 5


class TestPercentile:

    def test_top_of_history(self, scorer):
        history = [40, 50, 60, 70, 80]
        p = scorer.percentile(90, history)
        assert p == 100

    def test_bottom_of_history(self, scorer):
        history = [50, 60, 70, 80, 90]
        p = scorer.percentile(10, history)
        assert p == 0

    def test_middle(self, scorer):
        history = [20, 40, 60, 80]
        p = scorer.percentile(50, history)
        assert 25 <= p <= 75

    def test_empty_history(self, scorer):
        assert scorer.percentile(50, []) == 50


class TestScoreDay:
    """Test the module-level convenience function."""

    def test_score_day_basic(self):
        bd = score_day(
            productive_s=1800, total_screen_s=3600,
            distraction_count=3, longest_focus_s=1800,
        )
        assert 0 <= bd.final_score <= 100
        assert bd.letter_grade in ("A", "B", "C", "D", "F")
