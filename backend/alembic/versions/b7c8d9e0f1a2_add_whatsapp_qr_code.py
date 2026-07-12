"""add_whatsapp_qr_code_persist

Revision ID: b7c8d9e0f1a2
Revises: fbf8b351835b
Create Date: 2026-07-11 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, Sequence[str], None] = 'fbf8b351835b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('whatsapp_qr_code', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.drop_column('whatsapp_qr_code')
