"""
Unit tests for modules/assignments/parser.py

Tests every supported date format:
  weekday names, next <weekday>, tomorrow, in X days, month names, ISO dates
Also tests subject extraction, title cleaning, priority detection.
"""

from datetime import date, timedelta

from modules.assignments.parser import parse_assignment_command

# ── date parsing ──────────────────────────────────────────────────────────

class TestDateParsing:

    def test_weekday_friday(self):
        r = parse_assignment_command("Math assignment due Friday")
        assert r is not None
        assert r["due_date"] is not None
        # Due date should be the next Friday
        assert r["due_date"].strftime("%A") == "Friday"

    def test_next_monday(self):
        r = parse_assignment_command("Physics lab due next Monday")
        assert r is not None
        # "next Monday" should be at least 7 days from now if today is Monday
        assert r["due_date"] > date.today()
        assert r["due_date"].strftime("%A") == "Monday"

    def test_tomorrow(self):
        r = parse_assignment_command("Submit AI project tomorrow")
        assert r is not None
        assert r["due_date"] == date.today() + timedelta(days=1)

    def test_today(self):
        r = parse_assignment_command("Math quiz due today")
        assert r is not None
        assert r["due_date"] == date.today()

    def test_in_x_days(self):
        r = parse_assignment_command("DBMS homework due in 3 days")
        assert r is not None
        assert r["due_date"] == date.today() + timedelta(days=3)

    def test_in_1_day(self):
        r = parse_assignment_command("Essay due in 1 day")
        assert r is not None
        assert r["due_date"] == date.today() + timedelta(days=1)

    def test_month_name_june(self):
        r = parse_assignment_command("Economics essay due June 20")
        assert r is not None
        assert r["due_date"].month == 6
        assert r["due_date"].day == 20

    def test_iso_date(self):
        target = date.today() + timedelta(days=15)
        iso    = target.isoformat()
        r = parse_assignment_command(f"Computer networks assignment due {iso}")
        assert r is not None
        assert r["due_date"] == target

    def test_thursday(self):
        r = parse_assignment_command("add CS assignment due Thursday")
        assert r is not None
        assert r["due_date"].strftime("%A") == "Thursday"

    def test_returns_none_for_no_date(self):
        r = parse_assignment_command("Do some math")
        # No date in the string — should return None
        assert r is None


# ── subject extraction ────────────────────────────────────────────────────

class TestSubjectExtraction:

    def test_math_subject(self):
        r = parse_assignment_command("Math assignment due Friday")
        assert r is not None
        assert r["subject"] is not None
        assert "Math" in r["subject"]

    def test_physics_subject(self):
        r = parse_assignment_command("Physics lab report due next Monday")
        assert r is not None
        assert r["subject"] is not None
        assert "Physics" in r["subject"]

    def test_ai_subject(self):
        r = parse_assignment_command("Submit AI project tomorrow")
        assert r is not None
        assert r["subject"] is not None

    def test_dbms_subject(self):
        r = parse_assignment_command("DBMS homework due in 3 days")
        assert r is not None
        assert r["subject"] is not None

    def test_economics_subject(self):
        r = parse_assignment_command("economics essay due June 20")
        assert r is not None
        assert r["subject"] is not None
        assert "Economics" in r["subject"]

    def test_no_subject_still_works(self):
        # Should succeed even without a known subject
        r = parse_assignment_command("Submit report tomorrow")
        assert r is not None
        assert r["due_date"] == date.today() + timedelta(days=1)


# ── priority detection ────────────────────────────────────────────────────

class TestPriorityDetection:

    def test_urgent_flag(self):
        r = parse_assignment_command("urgent math test tomorrow")
        assert r is not None
        assert r["priority"] == "high"

    def test_important_flag(self):
        r = parse_assignment_command("important physics assignment due Friday")
        assert r is not None
        assert r["priority"] == "high"

    def test_default_medium(self):
        r = parse_assignment_command("Math assignment due Friday")
        assert r is not None
        assert r["priority"] == "medium"


# ── title cleaning ────────────────────────────────────────────────────────

class TestTitleCleaning:

    def test_no_date_in_title(self):
        r = parse_assignment_command("Math assignment due Friday")
        assert r is not None
        # Title should not contain "Friday" or "due"
        title_lower = r["title"].lower()
        assert "friday" not in title_lower
        assert r["title"]  # should not be empty

    def test_no_filler_words(self):
        r = parse_assignment_command("add math assignment due tomorrow")
        assert r is not None
        title_lower = r["title"].lower()
        assert "add" not in title_lower
        assert "tomorrow" not in title_lower

    def test_all_cases_return_non_empty_title(self):
        cases = [
            "Math assignment due Friday",
            "Submit AI project tomorrow",
            "DBMS homework due in 3 days",
            "Economics essay due June 20",
        ]
        for c in cases:
            r = parse_assignment_command(c)
            assert r is not None, f"Failed on: {c}"
            assert r["title"], f"Empty title for: {c}"
