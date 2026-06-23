"""extend agent_usages (Usage_Record): model_provider, fallback_reason, period

Revision ID: e4d5f6a7b8c9
Revises: d3c4e5f6a7b8
Create Date: 2026-06-10 10:15:00.000000

Feature: genia-agent-platform (Tarea 1.4)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e4d5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "d3c4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Anade columnas de proveedor/fallback/periodo al Usage_Record (agent_usages)."""
    with op.batch_alter_table("agent_usages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("model_provider", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("fallback_reason", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("period", sa.String(length=20), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_agent_usages_period"), ["period"], unique=False
        )


def downgrade() -> None:
    """Revierte las columnas anadidas a agent_usages."""
    with op.batch_alter_table("agent_usages", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_agent_usages_period"))
        batch_op.drop_column("period")
        batch_op.drop_column("fallback_reason")
        batch_op.drop_column("model_provider")
