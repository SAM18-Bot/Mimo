"""Add Todo table

Revision ID: 2be796c5c7f2
Revises: 060c21d35813
Create Date: 2026-08-23 09:01:07.135688

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '2be796c5c7f2'
down_revision: Union[str, None] = '060c21d35813'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('todos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=True),
    sa.Column('remind_at', sa.DateTime(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('delivered', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_todos_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_todos_user_id'), ['user_id'], unique=False)

def downgrade() -> None:
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_todos_user_id'))
        batch_op.drop_index(batch_op.f('ix_todos_id'))
    op.drop_table('todos')
