"""merge heads

Revision ID: 28cf1c81163c
Revises: 9a8b7c6d5e4f, b7c8d9e0f1a2
Create Date: 2026-07-15 12:18:19.060239

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28cf1c81163c'
down_revision: Union[str, Sequence[str], None] = ('9a8b7c6d5e4f', 'b7c8d9e0f1a2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
