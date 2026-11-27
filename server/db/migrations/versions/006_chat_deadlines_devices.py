"""Persist chat history, device provenance and normalized assignment deadlines."""
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import re

from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    schema = sa.inspect(bind)
    if not schema.has_table("chat_messages"):
        op.create_table(
            "chat_messages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("sender", sa.String(20), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime()),
        )
        op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])

    if "device" not in {col["name"] for col in schema.get_columns("screen_sessions")}:
        op.add_column("screen_sessions", sa.Column("device", sa.String(12), nullable=False, server_default="unknown"))

    users = sa.table("users", sa.column("ai_engine"), sa.column("api_key"))
    # Keep old credentials encrypted and inactive until their owner supplies a Gemini key.
    bind.execute(users.update().where(users.c.ai_engine != "gemini").values(
        ai_engine=sa.case((sa.func.coalesce(users.c.api_key, "") != "", "legacy"), else_="gemini")
    ))
    with op.batch_alter_table("users") as batch:
        batch.alter_column("ai_engine", existing_type=sa.String(20), server_default="gemini")

    assignments = sa.table("assignments", sa.column("id"), sa.column("user_id"), sa.column("due_time"), sa.column("notes"),
                           sa.column("due_date", sa.Date()))
    reminders = sa.table("reminders", sa.column("id"), sa.column("assignment_id"),
                         sa.column("delivered", sa.Boolean()), sa.column("message"),
                         sa.column("remind_at", sa.DateTime()))
    profiles = sa.table("schedule_profiles", sa.column("user_id"), sa.column("id"), sa.column("active", sa.Boolean()),
                        sa.column("timezone"), sa.column("created_at"))
    zones = {}
    for owner, name in bind.execute(sa.select(profiles.c.user_id, profiles.c.timezone)
                                    .where(profiles.c.active.is_(True))
                                    .order_by(profiles.c.created_at, profiles.c.id)):
        try:
            zones[owner] = ZoneInfo(name) if name and name != "local" else None
        except (ValueError, ZoneInfoNotFoundError):
            zones[owner] = None
    for row in bind.execute(sa.select(assignments)).mappings():
        raw = (row["due_time"] or "").strip().lower().replace(".", "")
        match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", raw)
        clock = None
        if match:
            hour, minute, suffix = int(match[1]), int(match[2] or 0), match[3]
            if minute < 60 and (1 <= hour <= 12 if suffix else hour < 24):
                clock = time(hour % 12 + 12 * (suffix == "pm") if suffix else hour, minute)
        if row["due_time"] is not None:
            values = {"due_time": clock.strftime("%H:%M") if clock else None}
            if raw and not clock:
                values["notes"] = "\n".join(filter(None, [row["notes"], "Original deadline time: " + row["due_time"]]))
            bind.execute(assignments.update().where(assignments.c.id == row["id"]).values(**values))
        pending = sa.select(reminders).where(reminders.c.assignment_id == row["id"], reminders.c.delivered.is_(False))
        for reminder in bind.execute(pending).mappings():
            wall_time = reminder["remind_at"]
            update = {}
            if clock:
                update["message"] = (reminder["message"] or "").rstrip() + f" Deadline: {clock:%H:%M}."
                if wall_time.date() == row["due_date"]:
                    wall_time = datetime.combine(row["due_date"], clock)
            update["remind_at"] = wall_time.replace(tzinfo=zones.get(row["user_id"])).astimezone(timezone.utc).replace(tzinfo=None)
            bind.execute(reminders.update().where(reminders.c.id == reminder["id"]).values(**update))


def downgrade():
    raise NotImplementedError("Restore a backup to reverse deadline normalization and preserve chat history.")
