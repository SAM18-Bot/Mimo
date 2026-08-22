"""
Natural language assignment parser.
Handles: weekday names, 'next Monday', 'tomorrow', 'in X days', 'June 20', ISO dates.
"""

import logging
import re
from datetime import date, timedelta

import dateparser

log = logging.getLogger(__name__)

KNOWN_SUBJECTS = {
    "math", "maths", "mathematics",
    "physics", "chemistry", "bio", "biology",
    "cs", "computer science", "dsa", "algorithms",
    "ai", "machine learning", "ml", "deep learning",
    "english", "history", "geography", "economics",
    "dbms", "database", "os", "operating systems",
    "networks", "computer networks",
}

_DAY_NAMES = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

_MONTH_RE = (
    r'(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?'
    r'|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
)


def _next_weekday(day_name: str) -> date:
    target = _DAY_NAMES[day_name.lower()]
    today  = date.today()
    delta  = (target - today.weekday()) % 7
    return today + timedelta(days=delta if delta else 7)


def parse_assignment_command(text: str) -> dict | None:
    text_low = text.strip().lower()
    due_date: date | None = None

    # 1. "next <weekday>"
    m = re.search(r'\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', text_low)
    if m:
        due_date = _next_weekday(m.group(1)) + timedelta(weeks=1)

    # 2. bare weekday  ("due friday")
    if not due_date:
        m = re.search(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', text_low)
        if m:
            due_date = _next_weekday(m.group(1))

    # 3. "in X days"
    if not due_date:
        m = re.search(r'\bin\s+(\d+)\s+days?\b', text_low)
        if m:
            due_date = date.today() + timedelta(days=int(m.group(1)))

    # 4. "tomorrow" / "today"
    if not due_date:
        if "tomorrow" in text_low:
            due_date = date.today() + timedelta(days=1)
        elif "today" in text_low:
            due_date = date.today()

    # 5. Calendar date: "June 20", "20 June", "June 20 2026"
    if not due_date:
        m = re.search(_MONTH_RE + r'\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\d{4})?', text_low, re.IGNORECASE)
        if not m:
            m = re.search(r'\d{1,2}(?:st|nd|rd|th)?\s+' + _MONTH_RE + r'(?:\s+\d{4})?', text_low, re.IGNORECASE)
        if m:
            parsed = dateparser.parse(m.group(0), settings={"PREFER_DATES_FROM": "future"})
            if parsed:
                due_date = parsed.date()

    # 6. ISO date: "2026-06-20"
    if not due_date:
        m = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text_low)
        if m:
            try:
                due_date = date.fromisoformat(m.group(1))
            except ValueError:
                pass

    # 7. Last resort: full dateparser pass
    if not due_date:
        parsed = dateparser.parse(text.strip(), settings={"PREFER_DATES_FROM": "future"})
        if parsed:
            due_date = parsed.date()

    if not due_date:
        log.warning("Could not parse date from: " + repr(text))
        return None

    # ── clean up title ────────────────────────────────────────────────────
    title = text_low

    # Remove filler verbs
    title = re.sub(r'\b(add|create|new|remind me to|submit)\b', '', title)
    # Remove assignment type words
    title = re.sub(r'\b(assignment|task|homework|project|lab|report|essay|test|exam|quiz)\b', '', title)
    # Remove date phrases
    title = re.sub(r'\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', '', title)
    title = re.sub(r'\b(due|by|on)\s+\w+', '', title)
    title = re.sub(r'\bin\s+\d+\s+days?\b', '', title)
    title = re.sub(r'\b(tomorrow|today|tonight)\b', '', title)
    title = re.sub(r'\b(urgent|important|asap)\b', '', title)
    title = re.sub(r'\b' + _MONTH_RE + r'\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\d{4})?\b', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '', title)
    title = re.sub(r'\s+', ' ', title).strip(" -—,.")

    # ── extract subject ───────────────────────────────────────────────────
    subject = None
    for subj in sorted(KNOWN_SUBJECTS, key=len, reverse=True):  # longest match first
        if re.search(r'\b' + re.escape(subj) + r'\b', title, re.IGNORECASE):
            subject = subj
            title = re.sub(r'\b' + re.escape(subj) + r'\b', '', title, flags=re.IGNORECASE).strip(" -—,.")
            break

    title = re.sub(r'\s+', ' ', title).strip(" -—,.")
    if not title:
        title = subject.title() if subject else "Assignment"

    priority = "high" if any(w in text_low for w in ["urgent", "important", "asap", "tonight"]) else "medium"

    return {
        "title":    title.title(),
        "subject":  subject.title() if subject else None,
        "due_date": due_date,
        "priority": priority,
    }
