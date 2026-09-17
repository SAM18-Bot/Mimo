"""Align persisted schema with the account-scoped application models.

Revision ID: 004
Revises: 2be796c5c7f2
Create Date: 2026-09-17

The early schema pre-dated accounts.  This migration assigns any existing
local data to a non-loginable legacy account, then makes ownership explicit
for every student-scoped table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: str | None = "2be796c5c7f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_EMAIL = "legacy-data@mimo.local"
OWNED_TABLES = (
    "screen_sessions",
    "cv_events",
    "assignments",
    "accountability_logs",
    "daily_summaries",
    "study_sessions",
    "roast_logs",
    "schedule_profiles",
)


def _inspector():
    return sa.inspect(op.get_bind())


def _column(table: str, name: str) -> dict | None:
    return next((item for item in _inspector().get_columns(table) if item["name"] == name), None)


def _has_index(table: str, name: str) -> bool:
    return any(item["name"] == name for item in _inspector().get_indexes(table))


def _has_user_foreign_key(table: str) -> bool:
    return any(
        item.get("referred_table") == "users" and item.get("constrained_columns") == ["user_id"]
        for item in _inspector().get_foreign_keys(table)
    )


def _has_rows_without_owner(table: str) -> bool:
    bind = op.get_bind()
    if _column(table, "user_id") is None:
        return bool(bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).scalar())
    return bool(bind.execute(sa.text(f"SELECT 1 FROM {table} WHERE user_id IS NULL LIMIT 1")).scalar())


def _legacy_user_id() -> int:
    bind = op.get_bind()
    existing = bind.execute(
        sa.text("SELECT id FROM users WHERE email = :email"), {"email": LEGACY_EMAIL}
    ).scalar()
    if existing is not None:
        return int(existing)

    op.bulk_insert(
        sa.table(
            "users",
            sa.column("email", sa.String()),
            sa.column("password_hash", sa.String()),
            sa.column("role", sa.String()),
            sa.column("display_name", sa.String()),
        ),
        [{
            "email": LEGACY_EMAIL,
            "password_hash": "!legacy-data-not-loginable!",
            "role": "student",
            "display_name": "Legacy local data",
        }],
    )
    return int(
        bind.execute(
            sa.text("SELECT id FROM users WHERE email = :email"), {"email": LEGACY_EMAIL}
        ).scalar_one()
    )


def _add_owner(table: str, legacy_user_id: int | None) -> None:
    column = _column(table, "user_id")
    if column is None:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        column = _column(table, "user_id")

    if _has_rows_without_owner(table):
        if legacy_user_id is None:
            raise RuntimeError(f"{table} has legacy rows but no legacy account")
        op.get_bind().execute(
            sa.text(f"UPDATE {table} SET user_id = :user_id WHERE user_id IS NULL"),
            {"user_id": legacy_user_id},
        )

    needs_non_null = bool(column and column.get("nullable", True))
    needs_foreign_key = not _has_user_foreign_key(table)
    if needs_non_null or needs_foreign_key:
        with op.batch_alter_table(table) as batch:
            if needs_non_null:
                batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
            if needs_foreign_key:
                batch.create_foreign_key(
                    f"fk_{table}_user_id_users", "users", ["user_id"], ["id"]
                )

    index_name = f"ix_{table}_user_id"
    if not _has_index(table, index_name):
        op.create_index(index_name, table, ["user_id"])


def _add_user_columns() -> None:
    additions = (
        sa.Column("ai_engine", sa.String(20), nullable=False, server_default="openai"),
        sa.Column("api_key", sa.String(255)),
        sa.Column("course", sa.String(120)),
        sa.Column("age", sa.Integer()),
        sa.Column("education_level", sa.String(50)),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("auth_provider", sa.String(50), nullable=False, server_default="local"),
        sa.Column("google_id", sa.String(255)),
    )
    for column in additions:
        if _column("users", column.name) is None:
            op.add_column("users", column)

    password_hash = _column("users", "password_hash")
    if password_hash and not password_hash.get("nullable", False):
        with op.batch_alter_table("users") as batch:
            batch.alter_column("password_hash", existing_type=sa.String(255), nullable=True)

    if not _has_index("users", "ix_users_google_id"):
        op.create_index("ix_users_google_id", "users", ["google_id"], unique=True)


def _add_token_blocklist() -> None:
    if "token_blocklist" in _inspector().get_table_names():
        return
    op.create_table(
        "token_blocklist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token", sa.String(500), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_token_blocklist_token", "token_blocklist", ["token"], unique=True)


def _replace_daily_summary_unique_constraint() -> None:
    inspector = _inspector()
    desired = {"user_id", "date"}
    constraints = inspector.get_unique_constraints("daily_summaries")
    if any(set(item.get("column_names") or []) == desired for item in constraints):
        return

    old = next(
        (item for item in constraints if item.get("column_names") == ["date"]), None
    )
    naming_convention = {"uq": "uq_%(table_name)s_%(column_0_name)s"}
    with op.batch_alter_table(
        "daily_summaries", recreate="always", naming_convention=naming_convention
    ) as batch:
        if old:
            batch.drop_constraint(old.get("name") or "uq_daily_summaries_date", type_="unique")
        batch.create_unique_constraint("uq_daily_summaries_user_date", ["user_id", "date"])


def _add_reminder_cascade() -> None:
    foreign_key = next(
        (
            item
            for item in _inspector().get_foreign_keys("reminders")
            if item.get("referred_table") == "assignments"
            and item.get("constrained_columns") == ["assignment_id"]
        ),
        None,
    )
    if foreign_key and (foreign_key.get("options") or {}).get("ondelete") == "CASCADE":
        return

    naming_convention = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}
    with op.batch_alter_table(
        "reminders", recreate="always", naming_convention=naming_convention
    ) as batch:
        if foreign_key:
            batch.drop_constraint(
                foreign_key.get("name") or "fk_reminders_assignment_id_assignments",
                type_="foreignkey",
            )
        batch.create_foreign_key(
            "fk_reminders_assignment_id_assignments",
            "assignments",
            ["assignment_id"],
            ["id"],
            ondelete="CASCADE",
        )


def upgrade() -> None:
    legacy_needed = any(_has_rows_without_owner(table) for table in OWNED_TABLES)
    legacy_user_id = _legacy_user_id() if legacy_needed else None

    for table in OWNED_TABLES:
        _add_owner(table, legacy_user_id)

    _replace_daily_summary_unique_constraint()
    _add_reminder_cascade()
    _add_user_columns()
    _add_token_blocklist()

    if _has_index("todos", "ix_todos_id"):
        op.drop_index("ix_todos_id", table_name="todos")


def downgrade() -> None:
    raise NotImplementedError(
        "This compatibility migration preserves account ownership and cannot be safely reversed."
    )
