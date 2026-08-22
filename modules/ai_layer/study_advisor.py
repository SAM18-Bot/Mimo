"""
study_advisor.py — AI-powered weekly study recommendations.

Analyses:
  - 7-day screen session history grouped by subject keywords
  - Assignment completion rate per subject
  - Peak productive hours from DailySummary
  - Overdue and upcoming assignments
  - Days since each subject was last studied

Generates:
  - Subject priority ranking (most neglected → study first)
  - Daily study plan with time slots
  - Resource recommendations per subject
  - AI narrative with OpenAI (or rule-based fallback)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from db.models import Assignment, ScreenSession
from modules.behavior_engine.pattern_detector import get_weekly_patterns

log = logging.getLogger(__name__)

# Minimum minutes per subject per week to be considered "studied"
STUDIED_THRESHOLD_MIN = 30


class StudyAdvisor:
    """
    Analyses a student's study patterns and generates recommendations.
    No side effects — all data passed in or read from DB read-only.
    """

    def __init__(self, db: Session):
        self._db = db

    # ── public API ────────────────────────────────────────────────────────

    def get_subject_report(self, user_id: int, days: int = 7) -> dict:
        """
        Returns a full subject-level analysis dict:
          subjects, weak_subjects, strong_subjects,
          time_per_subject, last_studied, recommendations
        """
        from db.models import User
        from modules.schedule.manager import get_active_profile
        
        user = self._db.get(User, user_id)
        api_key = user.api_key if user else None

        time_map   = self._subject_time(user_id, days)
        completion = self._completion_rates(user_id)
        last_seen  = self._last_studied(user_id)
        overdue    = self._overdue_subjects(user_id)
        patterns   = get_weekly_patterns(self._db, user_id=user_id)
        profile    = get_active_profile(self._db, user_id)
        
        profile_notes = profile.notes if profile and profile.notes else "No specific notes or year of study provided."

        ranked = self._rank_subjects(time_map, completion, last_seen, overdue)
        weak   = [s for s, _ in ranked[:3]]
        strong = [s for s, score in ranked if score > 70]

        plan    = self._build_study_plan(ranked, patterns.get("peak_productive_hour"))
        ai_data = self._ai_recommendations(time_map, completion, patterns, weak, profile_notes, api_key=api_key)
        ai_recs = ai_data.get("recommendations", [])
        suggested_subjects = ai_data.get("suggested_subjects", [])

        return {
            "analysis_date":      date.today().isoformat(),
            "days_analysed":      days,
            "subjects":           [s for s, _ in ranked],
            "weak_subjects":      weak,
            "strong_subjects":    strong,
            "time_per_subject":   {s: v for s, v in time_map.items()},
            "completion_rates":   completion,
            "last_studied":       {s: str(v) for s, v in last_seen.items()},
            "priority_ranking":   [{"subject": s, "need_score": round(n, 1)} for s, n in ranked],
            "daily_study_plan":   plan,
            "recommendations":    ai_recs,
            "suggested_subjects": suggested_subjects,
            "peak_hour":          patterns.get("peak_productive_hour"),
            "weekly_patterns":    patterns.get("insights", []),
        }

    def get_next_to_study(self, user_id: int) -> str:
        """Single answer: what to study right now."""
        overdue = self._overdue_subjects(user_id)
        if overdue:
            return f"You have overdue work in {overdue[0]}. Start there."

        time_map = self._subject_time(user_id, 7)
        if not time_map:
            upcoming = (
                self._db.query(Assignment)
                .filter(Assignment.user_id == user_id)
                .filter(Assignment.due_date >= date.today())
                .filter(Assignment.status != "done")
                .order_by(Assignment.due_date)
                .first()
            )
            if upcoming:
                return f"Work on '{upcoming.title}' — it's your next deadline."
            return "No clear priority detected. Review your weakest subject."

        least_studied = min(time_map, key=time_map.get)
        return (
            f"Study {least_studied} — you've only spent "
            f"{time_map[least_studied]}min on it this week."
        )

    # ── analysis helpers ─────────────────────────────────────────────────

    def _subject_time(self, user_id: int, days: int) -> dict[str, int]:
        """Minutes spent per subject over the past N days."""
        cutoff   = date.today() - timedelta(days=days)
        sessions = (
            self._db.query(ScreenSession)
            .filter(ScreenSession.user_id == user_id)
            .filter(ScreenSession.session_date >= cutoff)
            .filter(ScreenSession.category == "productive")
            .all()
        )

        totals: dict[str, int] = defaultdict(int)
        for s in sessions:
            subj = _extract_subject_from_title(s.window_title or s.app_name)
            if subj:
                totals[subj] += (s.duration_s or 0) // 60

        # Also add subjects from assignments (even if no screen time)
        assignments = (
            self._db.query(Assignment)
            .filter(Assignment.user_id == user_id)
            .filter(Assignment.due_date >= cutoff)
            .all()
        )
        for a in assignments:
            if a.subject and a.subject not in totals:
                totals[a.subject] = 0

        return dict(totals)

    def _completion_rates(self, user_id: int) -> dict[str, float]:
        """Assignment completion % per subject (0–100)."""
        assignments = self._db.query(Assignment).filter(Assignment.user_id == user_id).all()
        by_subject: dict[str, list] = defaultdict(list)
        for a in assignments:
            if a.subject:
                by_subject[a.subject].append(a.status == "done")

        return {
            subj: round(sum(done_list) / len(done_list) * 100, 1)
            for subj, done_list in by_subject.items()
            if done_list
        }

    def _last_studied(self, user_id: int) -> dict[str, date]:
        """Date each subject was last seen in productive screen sessions."""
        sessions = (
            self._db.query(ScreenSession)
            .filter(ScreenSession.user_id == user_id)
            .filter(ScreenSession.category == "productive")
            .order_by(ScreenSession.session_date.desc())
            .limit(500)
            .all()
        )
        last: dict[str, date] = {}
        for s in sessions:
            subj = _extract_subject_from_title(s.window_title or "")
            if subj and subj not in last and s.session_date:
                last[subj] = s.session_date
        return last

    def _overdue_subjects(self, user_id: int) -> list[str]:
        overdue = (
            self._db.query(Assignment)
            .filter(Assignment.user_id == user_id)
            .filter(Assignment.due_date < date.today())
            .filter(Assignment.status != "done")
            .all()
        )
        seen = set()
        result = []
        for a in overdue:
            s = a.subject or a.title
            if s not in seen:
                seen.add(s)
                result.append(s)
        return result

    # ── priority ranking ──────────────────────────────────────────────────

    def _rank_subjects(
        self,
        time_map:   dict[str, int],
        completion: dict[str, float],
        last_seen:  dict[str, date],
        overdue:    list[str],
    ) -> list[tuple[str, float]]:
        """
        Returns subjects sorted by "need score" descending (most needed first).
        Need score = 100 - normalized_time - completion_rate + staleness_days
        """
        all_subjects = set(time_map) | set(completion) | set(last_seen)
        max_time = max(time_map.values(), default=1) or 1

        ranked = []
        for subj in all_subjects:
            time_pts       = (time_map.get(subj, 0) / max_time) * 40
            comp_pts       = completion.get(subj, 50) / 100 * 30
            days_ago       = (date.today() - last_seen[subj]).days if subj in last_seen else 14
            staleness_pts  = min(days_ago * 2, 30)
            overdue_bonus  = 20 if subj in overdue else 0

            need_score = 100 - time_pts - comp_pts + staleness_pts + overdue_bonus
            ranked.append((subj, min(100, max(0, need_score))))

        return sorted(ranked, key=lambda x: x[1], reverse=True)

    # ── study plan ────────────────────────────────────────────────────────

    def _build_study_plan(
        self,
        ranked:    list[tuple[str, float]],
        peak_hour: int | None,
    ) -> list[dict]:
        """Build a simple time-blocked daily plan for the top 3 subjects."""
        top3 = [s for s, _ in ranked[:3]]
        if not top3:
            return []

        start_hour = peak_hour if peak_hour is not None else 9
        plan = []

        for i, subj in enumerate(top3):
            slot_start = (start_hour + i * 2) % 24
            slot_end   = (slot_start + 2) % 24
            plan.append({
                "subject":    subj,
                "start_time": f"{slot_start:02d}:00",
                "end_time":   f"{slot_end:02d}:00",
                "duration_min": 120,
                "reason":     "Lowest study time this week among your subjects.",
            })

        return plan

    # ── AI recommendations ────────────────────────────────────────────────

    def _ai_recommendations(
        self,
        time_map:  dict[str, int],
        completion: dict[str, float],
        patterns:  dict,
        weak:      list[str],
        profile_notes: str,
        api_key: str | None = None,
    ) -> dict:
        """
        Try AI-generated recommendations. Falls back to rule-based if no API key.
        Returns a dict: {"recommendations": [...], "suggested_subjects": [...]}
        """
        try:
            from modules.ai_layer.client import generate_study_recommendations
            context = {
                "profile_notes":    profile_notes,
                "weekly_data":      patterns.get("weekly_data", "No data"),
                "weak_subjects":    ", ".join(weak) if weak else "none identified",
                "peak_window":      _fmt_peak(patterns.get("peak_productive_hour")),
                "avg_study_min":    patterns.get("avg_productive_min", 0),
                "completion_rate":  patterns.get("completion_rate_pct", 0),
            }
            recs = generate_study_recommendations(context, api_key=api_key)
            if recs:
                return recs
        except Exception as e:
            log.debug("AI recommendations failed: %s", e)

        # Rule-based fallback
        return {
            "recommendations": _rule_based_recommendations(time_map, completion, weak),
            "suggested_subjects": []
        }


# ── subject extraction from window titles ────────────────────────────────

_SUBJECT_KEYWORDS = {
    "math":             ["math", "calculus", "algebra", "statistics", "numpy", "scipy"],
    "physics":          ["physics", "mechanics", "thermodynamics", "optics"],
    "chemistry":        ["chemistry", "organic", "periodic", "reaction"],
    "biology":          ["biology", "genetics", "cell", "ecology"],
    "computer science": ["python", "java", "c++", "leetcode", "dsa", "algorithm", "code"],
    "ai/ml":            ["machine learning", "deep learning", "tensorflow", "pytorch", "neural"],
    "economics":        ["economics", "micro", "macro", "gdp", "inflation"],
    "english":          ["essay", "grammar", "writing", "literature", "shakespeare"],
    "databases":        ["sql", "mysql", "postgres", "mongodb", "dbms"],
    "networks":         ["networking", "tcp", "http", "dns", "socket"],
}


def _extract_subject_from_title(text: str) -> str | None:
    text_low = (text or "").lower()
    for subject, keywords in _SUBJECT_KEYWORDS.items():
        if any(kw in text_low for kw in keywords):
            return subject
    return None


def _fmt_peak(hour: int | None) -> str:
    if hour is None:
        return "unknown"
    suffix = "AM" if hour < 12 else "PM"
    h = hour if hour <= 12 else hour - 12
    return f"{h}:00 {suffix}"


def _rule_based_recommendations(
    time_map: dict[str, int],
    completion: dict[str, float],
    weak: list[str],
) -> list[dict]:
    recs = []
    if weak:
        recs.append({
            "recommendation": (
                f"Prioritise {weak[0]} — it has the lowest study time this week. "
                f"Aim for at least 90 minutes on it tomorrow."
            ),
            "priority": "high",
        })
    if len(weak) > 1:
        recs.append({
            "recommendation": (
                f"Schedule {weak[1]} for your second study block. "
                f"Use active recall, not just re-reading."
            ),
            "priority": "medium",
        })

    low_completion = [s for s, r in completion.items() if r < 50]
    if low_completion:
        recs.append({
            "recommendation": (
                f"Your assignment completion rate for {low_completion[0]} is below 50%. "
                f"Break pending tasks into 30-minute chunks."
            ),
            "priority": "high",
        })

    if not recs:
        recs.append({
            "recommendation": "Keep your current routine. Track for 7 days for personalised insights.",
            "priority": "medium",
        })

    return recs


# ── FastAPI router ────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from api.routes_auth import current_user
from db.database import get_db
from db.models import User

router = APIRouter(prefix="/study", tags=["study"])


@router.get("/recommendations")
def get_recommendations(days: int = 7, user: User = Depends(current_user), db: DbSession = Depends(get_db)):
    """Full weekly subject analysis + study plan + AI recommendations."""
    advisor = StudyAdvisor(db)
    return advisor.get_subject_report(user.id, days=days)


@router.get("/next")
def what_to_study_now(user: User = Depends(current_user), db: DbSession = Depends(get_db)):
    """Single answer: what to study right now."""
    advisor = StudyAdvisor(db)
    return {"recommendation": advisor.get_next_to_study(user.id)}


@router.get("/subjects")
def subject_time_breakdown(days: int = 7, user: User = Depends(current_user), db: DbSession = Depends(get_db)):
    """Raw minutes per subject over the past N days."""
    advisor = StudyAdvisor(db)
    return advisor._subject_time(user.id, days)
