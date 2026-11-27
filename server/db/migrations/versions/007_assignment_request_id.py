"""Deduplicate retried mobile assignment creates within an account."""
import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    schema = sa.inspect(op.get_bind())
    if "request_id" not in {item["name"] for item in schema.get_columns("assignments")}:
        op.add_column("assignments", sa.Column("request_id", sa.String(36)))
    if "ix_assignments_user_request" not in {item["name"] for item in schema.get_indexes("assignments")}:
        op.create_index("ix_assignments_user_request", "assignments", ["user_id", "request_id"], unique=True)


def downgrade():
    op.drop_index("ix_assignments_user_request", table_name="assignments")
    with op.batch_alter_table("assignments") as batch:
        batch.drop_column("request_id")
