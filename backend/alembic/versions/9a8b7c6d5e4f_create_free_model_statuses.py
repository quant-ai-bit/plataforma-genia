"""create_free_model_statuses

Revision ID: 9a8b7c6d5e4f
Revises: fbf8b351835b
Create Date: 2026-07-08 11:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a8b7c6d5e4f'
down_revision: Union[str, Sequence[str], None] = 'fbf8b351835b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'free_model_statuses',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('is_exhausted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('exhausted_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exhausted_reason', sa.String(length=255), nullable=True),
        sa.Column('tokens_used_today', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('requests_used_today', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('last_used', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('free_model_statuses')
