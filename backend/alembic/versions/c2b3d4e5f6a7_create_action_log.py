"""create action_log con indices de auditoria

Revision ID: c2b3d4e5f6a7
Revises: b1a2c3d4e5f6
Create Date: 2026-06-10 10:05:00.000000

Feature: genia-agent-platform (Tarea 1.2)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2b3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "b1a2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea la tabla action_log con indices en tenant_id y created_at."""
    op.create_table(
        "action_log",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("tool_name", sa.String(length=255), nullable=False),
        sa.Column("input_params", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("model_provider", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("action_log", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_action_log_tenant_id"), ["tenant_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_action_log_created_at"), ["created_at"], unique=False
        )


def downgrade() -> None:
    """Elimina la tabla action_log."""
    with op.batch_alter_table("action_log", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_action_log_created_at"))
        batch_op.drop_index(batch_op.f("ix_action_log_tenant_id"))
    op.drop_table("action_log")
