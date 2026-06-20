"""Initial schema — all 8 tables

Revision ID: 001
Revises: —
Create Date: 2026-06-08

Tables created:
  screen_sessions, cv_events, assignments, reminders,
  accountability_logs, daily_summaries, study_sessions, roast_logs
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision:       str                            = "001"
down_revision:  Union[str, None]               = None
branch_labels:  Union[str, Sequence[str], None] = None
depends_on:     Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "screen_sessions",
        sa.Column("id",           sa.Integer(),    primary_key=True),
        sa.Column("app_name",     sa.String(200),  nullable=False),
        sa.Column("window_title", sa.String(500)),
        sa.Column("category",     sa.String(20)),
        sa.Column("started_at",   sa.DateTime(),   nullable=False),
        sa.Column("ended_at",     sa.DateTime()),
        sa.Column("duration_s",   sa.Integer(),    default=0),
        sa.Column("session_date", sa.Date()),
    )
    op.create_index("ix_screen_sessions_session_date", "screen_sessions", ["session_date"])

    op.create_table(
        "cv_events",
        sa.Column("id",           sa.Integer(),   primary_key=True),
        sa.Column("event_type",   sa.String(20)),
        sa.Column("timestamp",    sa.DateTime(),  nullable=False),
        sa.Column("session_date", sa.Date()),
    )
    op.create_index("ix_cv_events_session_date", "cv_events", ["session_date"])

    op.create_table(
        "assignments",
        sa.Column("id",          sa.Integer(),    primary_key=True),
        sa.Column("title",       sa.String(300),  nullable=False),
        sa.Column("subject",     sa.String(100)),
        sa.Column("due_date",    sa.Date(),       nullable=False),
        sa.Column("priority",    sa.String(20),   server_default="medium"),
        sa.Column("status",      sa.String(20),   server_default="pending"),
        sa.Column("notes",       sa.Text()),
        sa.Column("created_at",  sa.DateTime()),
        sa.Column("reminded_at", sa.DateTime()),
    )
    op.create_index("ix_assignments_due_date", "assignments", ["due_date"])
    op.create_index("ix_assignments_status",   "assignments", ["status"])

    op.create_table(
        "reminders",
        sa.Column("id",            sa.Integer(),   primary_key=True),
        sa.Column("assignment_id", sa.Integer(),   sa.ForeignKey("assignments.id")),
        sa.Column("remind_at",     sa.DateTime(),  nullable=False),
        sa.Column("delivered",     sa.Boolean(),   server_default="0"),
        sa.Column("message",       sa.Text()),
    )
    op.create_index("ix_reminders_remind_at",  "reminders", ["remind_at"])
    op.create_index("ix_reminders_delivered",  "reminders", ["delivered"])

    op.create_table(
        "accountability_logs",
        sa.Column("id",          sa.Integer(), primary_key=True),
        sa.Column("date",        sa.Date(),    nullable=False),
        sa.Column("question",    sa.Text()),
        sa.Column("answer",      sa.Text()),
        sa.Column("recorded_at", sa.DateTime()),
    )

    op.create_table(
        "daily_summaries",
        sa.Column("id",                 sa.Integer(), primary_key=True),
        sa.Column("date",               sa.Date(),    unique=True, nullable=False),
        sa.Column("productive_time_s",  sa.Integer(), server_default="0"),
        sa.Column("distracted_time_s",  sa.Integer(), server_default="0"),
        sa.Column("neutral_time_s",     sa.Integer(), server_default="0"),
        sa.Column("desk_time_s",        sa.Integer(), server_default="0"),
        sa.Column("absent_time_s",      sa.Integer(), server_default="0"),
        sa.Column("focus_score",        sa.Float(),   server_default="0.0"),
        sa.Column("distraction_count",  sa.Integer(), server_default="0"),
        sa.Column("assignments_due",    sa.Integer(), server_default="0"),
        sa.Column("assignments_done",   sa.Integer(), server_default="0"),
        sa.Column("ai_report_text",     sa.Text()),
        sa.Column("peak_hour",          sa.Integer()),
        sa.Column("created_at",         sa.DateTime()),
    )
    op.create_index("ix_daily_summaries_date", "daily_summaries", ["date"])

    op.create_table(
        "study_sessions",
        sa.Column("id",         sa.Integer(), primary_key=True),
        sa.Column("subject",    sa.String(100)),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at",   sa.DateTime()),
        sa.Column("duration_s", sa.Integer()),
        sa.Column("source",     sa.String(20), server_default="auto"),
    )

    op.create_table(
        "roast_logs",
        sa.Column("id",           sa.Integer(), primary_key=True),
        sa.Column("trigger",      sa.String(100)),
        sa.Column("message",      sa.Text()),
        sa.Column("timestamp",    sa.DateTime()),
        sa.Column("session_date", sa.Date()),
    )
    op.create_index("ix_roast_logs_session_date", "roast_logs", ["session_date"])


def downgrade() -> None:
    for tbl in [
        "roast_logs", "study_sessions", "daily_summaries",
        "accountability_logs", "reminders", "assignments",
        "cv_events", "screen_sessions",
    ]:
        op.drop_table(tbl)
