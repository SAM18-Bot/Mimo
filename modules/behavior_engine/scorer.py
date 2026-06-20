"""
scorer.py — Standalone productivity scoring engine.

Extracted from aggregator.py so it can be:
  - Unit tested without DB
  - Configured independently
  - Reused by routes and the AI layer

Score model (0–100):
  Productive ratio   up to 60 pts  (productive_s / total_screen_s)
  Presence quality   up to 30 pts  (present CV events vs total)
  Context switch penalty  -2 per switch, max -20
  Long focus bonus        +10 for 60+ min uninterrupted session

Letter grades:  A ≥ 85 | B ≥ 70 | C ≥ 50 | D ≥ 35 | F < 35
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional

log = logging.getLogger(__name__)


# ── score result ──────────────────────────────────────────────────────────

@dataclass
class ScoreBreakdown:
    final_score:        float   # 0–100
    productive_pts:     float   # 0–60
    presence_pts:       float   # 0–30
    switch_penalty:     float   # 0 to -20
    focus_bonus:        float   # 0 or +10
    letter_grade:       str     # A / B / C / D / F
    verdict:            str     # one-line human label
    productive_ratio:   float   # 0.0–1.0
    presence_ratio:     float   # 0.0–1.0
    distraction_count:  int
    longest_focus_min:  int


# ── scorer class ──────────────────────────────────────────────────────────

class ProductivityScorer:
    """
    Pure-function scorer — no DB access, no side effects.
    All inputs passed explicitly so the logic is fully testable.
    """

    # ── weights (can be tuned in config later) ─────────────────────────
    MAX_PRODUCTIVE_PTS = 60.0
    MAX_PRESENCE_PTS   = 30.0
    SWITCH_PENALTY_PER = 2.0     # per context switch
    MAX_SWITCH_PENALTY = 20.0
    LONG_FOCUS_BONUS   = 10.0
    LONG_FOCUS_MIN_S   = 3600    # 60 minutes to earn the bonus

    def compute(
        self,
        productive_s:      int,
        total_screen_s:    int,
        present_events:    int,
        total_cv_events:   int,
        distraction_count: int,   # context switches to distracting apps
        longest_focus_s:   int,
    ) -> ScoreBreakdown:
        """
        Compute full score breakdown from raw counters.
        All values are for a single day / session window.
        """
        # ── productive ratio component ─────────────────────────────────
        prod_ratio  = productive_s / total_screen_s if total_screen_s > 0 else 0.0
        prod_pts    = prod_ratio * self.MAX_PRODUCTIVE_PTS

        # ── presence / CV component ────────────────────────────────────
        pres_ratio  = present_events / total_cv_events if total_cv_events > 0 else 0.0
        pres_pts    = pres_ratio * self.MAX_PRESENCE_PTS

        # ── context switch penalty ──────────────────────────────────────
        penalty = min(distraction_count * self.SWITCH_PENALTY_PER, self.MAX_SWITCH_PENALTY)

        # ── long focus bonus ────────────────────────────────────────────
        bonus   = self.LONG_FOCUS_BONUS if longest_focus_s >= self.LONG_FOCUS_MIN_S else 0.0

        # ── final ───────────────────────────────────────────────────────
        raw   = prod_pts + pres_pts - penalty + bonus
        score = round(max(0.0, min(100.0, raw)), 1)
        grade = self.letter_grade(score)

        return ScoreBreakdown(
            final_score       = score,
            productive_pts    = round(prod_pts, 1),
            presence_pts      = round(pres_pts, 1),
            switch_penalty    = round(-penalty, 1),
            focus_bonus       = bonus,
            letter_grade      = grade,
            verdict           = self._verdict(score),
            productive_ratio  = round(prod_ratio, 3),
            presence_ratio    = round(pres_ratio, 3),
            distraction_count = distraction_count,
            longest_focus_min = longest_focus_s // 60,
        )

    # ── convenience: simple score (backward compatible with old aggregator) ─
    def simple_score(
        self,
        productive_s:      int,
        total_screen_s:    int,
        distraction_count: int,
    ) -> float:
        """Quick score without CV data. Used when camera is offline."""
        if total_screen_s == 0:
            return 0.0
        ratio   = productive_s / total_screen_s
        penalty = min(distraction_count * 2, 30)
        return round(max(0.0, min(100.0, ratio * 100 - penalty)), 1)

    # ── grades ─────────────────────────────────────────────────────────
    @staticmethod
    def letter_grade(score: float) -> str:
        if score >= 85: return "A"
        if score >= 70: return "B"
        if score >= 50: return "C"
        if score >= 35: return "D"
        return "F"

    @staticmethod
    def _verdict(score: float) -> str:
        if score >= 85: return "Excellent day — keep this up."
        if score >= 70: return "Solid. A few distractions, but mostly on track."
        if score >= 50: return "Mediocre. You can do better."
        if score >= 35: return "Poor. Most of your time was wasted."
        return "Terrible. You basically didn't study today."

    # ── streak ─────────────────────────────────────────────────────────
    @staticmethod
    def compute_streak(daily_scores: List[float], threshold: float = 50.0) -> int:
        """
        Count consecutive days (most recent first) where score >= threshold.
        Pass today's score first.
        """
        streak = 0
        for s in daily_scores:
            if s >= threshold:
                streak += 1
            else:
                break
        return streak

    # ── percentile vs history ───────────────────────────────────────────
    @staticmethod
    def percentile(score: float, history: List[float]) -> int:
        """Return what percentile today's score is vs the history list."""
        if not history:
            return 50
        below = sum(1 for h in history if h < score)
        return round((below / len(history)) * 100)


# ── module-level singleton ────────────────────────────────────────────────
default_scorer = ProductivityScorer()


def score_day(
    productive_s:      int,
    total_screen_s:    int,
    present_events:    int     = 0,
    total_cv_events:   int     = 0,
    distraction_count: int     = 0,
    longest_focus_s:   int     = 0,
) -> ScoreBreakdown:
    """Module-level convenience function."""
    return default_scorer.compute(
        productive_s      = productive_s,
        total_screen_s    = total_screen_s,
        present_events    = present_events,
        total_cv_events   = total_cv_events,
        distraction_count = distraction_count,
        longest_focus_s   = longest_focus_s,
    )
