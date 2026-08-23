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
    due_time: str | None = None

    time_m = re.search(r'\b(?:at|by)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.|\s*o\'clock|))', text_low)
    if not time_m:
        time_m = re.search(r'\b(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.))\b', text_low)
    
    if time_m:
        t_str = time_m.group(1).replace('.', '').replace(' ', '').strip()
        if t_str and not t_str.isdigit():
            due_time = t_str

    m = re.search(r'\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', text_low)
    if m:
        due_date = _next_weekday(m.group(1)) + timedelta(weeks=1)

    if not due_date:
        m = re.search(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', text_low)
        if m:
            due_date = _next_weekday(m.group(1))

    if not due_date:
        m = re.search(r'\bin\s+(\d+)\s+days?\b', text_low)
        if m:
            due_date = date.today() + timedelta(days=int(m.group(1)))

    if not due_date:
        if "tomorrow" in text_low:
            due_date = date.today() + timedelta(days=1)
        elif "today" in text_low:
            due_date = date.today()

    if not due_date:
        m = re.search(_MONTH_RE + r'\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\d{4})?', text_low, re.IGNORECASE)
        if not m:
            m = re.search(r'\d{1,2}(?:st|nd|rd|th)?\s+' + _MONTH_RE + r'(?:\s+\d{4})?', text_low, re.IGNORECASE)
        if m:
            parsed = dateparser.parse(m.group(0), settings={"PREFER_DATES_FROM": "future"})
            if parsed:
                due_date = parsed.date()

    if not due_date:
        m = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text_low)
        if m:
            try:
                due_date = date.fromisoformat(m.group(1))
            except ValueError:
                pass

    if not due_date:
        parsed = dateparser.parse(text.strip(), settings={"PREFER_DATES_FROM": "future"})
        if parsed:
            due_date = parsed.date()

    if not due_date:
        log.warning("Could not parse date from: " + repr(text))
        return None

    title = text_low

    title = re.sub(r'\b(add|create|new|remind me to|submit)\b', '', title)
    title = re.sub(r'\b(assignment|task|homework|project|lab|report|essay|test|exam|quiz)\b', '', title)
    title = re.sub(r'\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', '', title)
    title = re.sub(r'\bin\s+\d+\s+days?\b', '', title)
    title = re.sub(r'\b(tomorrow|today|tonight)\b', '', title)
    title = re.sub(r'\b' + _MONTH_RE + r'\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\d{4})?\b', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '', title)
    
    title = re.sub(r'\b(?:at|by)\s+\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.|\s*o\'clock|)\b', '', title)
    title = re.sub(r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)\b', '', title)

    title = re.sub(r'\b(due|by|on)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', '', title)
    title = re.sub(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', '', title)
    title = re.sub(r'\b(due|by|on)\b', '', title)
    
    title = re.sub(r'\b(urgent|important|asap)\b', '', title)
    
    subject = None
    for subj in sorted(KNOWN_SUBJECTS, key=len, reverse=True):
        if re.search(r'\b' + re.escape(subj) + r'\b', title, re.IGNORECASE):
            subject = subj
            title = re.sub(r'\b' + re.escape(subj) + r'\b', '', title, flags=re.IGNORECASE)
            break

    title = re.sub(r'\s+', ' ', title).strip(" -—.,")
    if not title:
        title = subject.title() if subject else "Assignment"

    priority = "high" if any(w in text_low for w in ["urgent", "important", "asap", "tonight"]) else "medium"

    return {
        "title":    title.title(),
        "subject":  subject.title() if subject else None,
        "due_date": due_date,
        "due_time": due_time,
        "priority": priority,
    }
