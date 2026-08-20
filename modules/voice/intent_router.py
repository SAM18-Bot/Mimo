"""
Intent router — maps recognized voice text to system actions.
Uses simple keyword matching (fast, no LLM needed for commands).

Supported intents:
  add_assignment  : "add assignment math due friday"
  show_tasks      : "show my tasks" / "what do I have today"
  mark_done       : "done with physics" / "mark math as done"
  start_session   : "start study session"
  productivity    : "how productive was I" / "my score today"
  what_to_study   : "what should I study"
  eod_report      : "give me my report"
"""

import logging
import re
from typing import Optional

log = logging.getLogger(__name__)


class IntentRouter:
    def __init__(
        self,
        speak_fn=None,
        broadcast_fn=None,
        user_id: int = 1,
    ):
        self._speak     = speak_fn
        self._broadcast = broadcast_fn
        self._user_id   = user_id

    def route(self, text: str):
        text = text.lower().strip()
        log.info(f"Routing intent: {text!r}")

        intent = self._detect_intent(text)

        if intent == "add_assignment":
            self._handle_add_assignment(text)
        elif intent == "show_tasks":
            self._handle_show_tasks()
        elif intent == "mark_done":
            self._handle_mark_done(text)
        elif intent == "productivity":
            self._handle_productivity()
        elif intent == "what_to_study":
            self._handle_what_to_study()
        elif intent == "eod_report":
            self._handle_eod_report()
        elif intent == "ask_coach":
            self._handle_ask_coach(text)
        else:
            if self._speak:
                self._speak("I didn't catch that. Try: add assignment, show tasks, or how productive was I.")

    # ── intent detection ──────────────────────────────────────────────────
    def _detect_intent(self, text: str) -> str:
        if any(w in text for w in ["add assignment", "add task", "new assignment", "homework", "due"]):
            return "add_assignment"
        if any(w in text for w in ["show tasks", "my tasks", "what do i have", "today's tasks"]):
            return "show_tasks"
        if any(w in text for w in ["done with", "mark", "finished", "completed", "submitted"]):
            return "mark_done"
        if any(w in text for w in ["productive", "how was my day", "focus score", "my score"]):
            return "productivity"
        if any(w in text for w in ["what should i study", "recommend", "what to study"]):
            return "what_to_study"
        if any(w in text for w in ["end of day", "my report", "daily report", "summary"]):
            return "eod_report"
        if any(w in text for w in ["coach", "ask", "tell me", "help", "explain", "what is", "who is", "why", "how do", "can you"]):
            return "ask_coach"
        # Since ask_coach handles generic things, let's treat unknown as ask_coach as well to allow free-flowing questions
        return "ask_coach"

    # ── handlers ─────────────────────────────────────────────────────────
    def _handle_add_assignment(self, text: str):
        from modules.assignments.parser import parse_assignment_command
        from db.database import get_db_ctx
        from modules.assignments.manager import create_assignment

        result = parse_assignment_command(text)
        if not result:
            if self._speak:
                self._speak("I couldn't parse that assignment. Try: add Math assignment due Friday.")
            return

        with get_db_ctx() as db:
            a = create_assignment(
                db       = db,
                title    = result["title"],
                subject  = result.get("subject"),
                due_date = result["due_date"],
                priority = result.get("priority", "medium"),
                user_id  = self._user_id,
            )
            # Capture values before session closes to avoid DetachedInstanceError
            a_id, a_title, a_subject, a_due, a_priority, a_status = (
                a.id, a.title, a.subject, a.due_date, a.priority, a.status
            )

        msg = f"Added: {a_title}, due {a_due}."
        if self._speak:
            self._speak(msg)
        if self._broadcast:
            self._broadcast({"type": "assignment_added", "assignment": {
                "id":       a_id,
                "title":    a_title,
                "subject":  a_subject,
                "due_date": str(a_due),
                "priority": a_priority,
                "status":   a_status,
            }})

    def _handle_show_tasks(self):
        from db.database import get_db_ctx
        from modules.assignments.manager import get_upcoming

        with get_db_ctx() as db:
            tasks = get_upcoming(db, days=7, user_id=self._user_id)
            task_list = [
                {"id": a.id, "title": a.title, "due_date": str(a.due_date), "status": a.status}
                for a in tasks
            ]

        if not task_list:
            if self._speak:
                self._speak("No upcoming assignments in the next 7 days. Either you're ahead, or you've given up.")
            return

        summary = f"You have {len(task_list)} upcoming assignments. "
        lines = [f"{t['title']}, due {t['due_date']}" for t in task_list[:3]]
        summary += ". ".join(lines)
        if len(task_list) > 3:
            summary += f". And {len(task_list)-3} more."

        if self._speak:
            self._speak(summary)
        if self._broadcast:
            self._broadcast({"type": "tasks_list", "tasks": task_list})

    def _handle_mark_done(self, text: str):
        from db.database import get_db_ctx
        from db.models import Assignment
        from modules.assignments.manager import mark_done

        # Extract subject/title hint
        for w in ["done with", "mark", "finished", "completed", "submitted"]:
            text = text.replace(w, "").strip()
        keyword = text.strip()

        with get_db_ctx() as db:
            candidates = db.query(Assignment).filter(
                Assignment.user_id == self._user_id,
                Assignment.status != "done",
                Assignment.title.ilike(f"%{keyword}%")
            ).all()
            if not candidates:
                if self._speak:
                    self._speak(f"I couldn't find a pending assignment matching '{keyword}'.")
                return
            a = mark_done(db, candidates[0].id, user_id=self._user_id)
            a_title = a.title

        if self._speak:
            self._speak(f"Marked '{a_title}' as done. Good. Now do the next one.")

    def _handle_productivity(self):
        from db.database import get_db_ctx
        from modules.behavior_engine.aggregator import get_daily_stats

        with get_db_ctx() as db:
            stats = get_daily_stats(db, user_id=self._user_id)

        score = stats["focus_score"]
        prod  = stats["productive_min"]
        dist  = stats["distracting_min"]

        msg = (
            f"Today's focus score is {score} out of 100. "
            f"You studied for {prod} minutes and wasted {dist} minutes on distracting apps."
        )
        if score < 40:
            msg += " That's rough. You can do better."
        elif score < 70:
            msg += " Decent, but you left a lot on the table."
        else:
            msg += " Good work today."

        if self._speak:
            self._speak(msg)

    def _handle_what_to_study(self):
        from db.database import get_db_ctx
        try:
            from modules.ai_layer.study_advisor import StudyAdvisor
            with get_db_ctx() as db:
                advisor = StudyAdvisor(db)
                msg     = advisor.get_next_to_study(user_id=self._user_id)
        except Exception:
            # Fallback to simple assignment-based advice
            from modules.assignments.manager import get_upcoming
            with get_db_ctx() as db:
                upcoming = get_upcoming(db, user_id=self._user_id, days=5)
                if not upcoming:
                    msg = "No assignments due soon. Review your weakest subject or get ahead on readings."
                else:
                    most_urgent = upcoming[0]
                    msg = f"Your most urgent assignment is '{most_urgent.title}', due {most_urgent.due_date}. Start with that."

        if self._speak:
            self._speak(msg)
        if self._broadcast:
            self._broadcast({"type": "study_advice", "message": msg})

    def _handle_eod_report(self):
        from modules.ai_layer.daily_report import run_eod_report
        if self._speak:
            self._speak("Generating your end of day report. Give me a moment.")
        run_eod_report(speak_fn=self._speak, broadcast_fn=self._broadcast)

    def _handle_ask_coach(self, text: str):
        from db.database import get_db_ctx
        from modules.ai_layer.client import generate_coach_response
        from modules.behavior_engine.aggregator import get_daily_stats
        from modules.ai_layer.roast_engine import RoastEngine

        # Get stats
        with get_db_ctx() as db:
            stats = get_daily_stats(db, user_id=self._user_id)
        
        # Get pending assignments
        engine = RoastEngine()
        context_data = engine._get_context(self._user_id)

        context = {
            "pending_assignments": context_data.get("pending_assignments", ""),
            "focus_score": stats.get("focus_score", 0),
            "productive_min": stats.get("productive_min", 0),
            "distracting_min": stats.get("distracting_min", 0)
        }

        if self._speak:
            self._speak("Let me think about that.")

        response = generate_coach_response(text, context)

        if self._speak:
            self._speak(response)
        if self._broadcast:
            self._broadcast({"type": "voice_response", "message": response})
