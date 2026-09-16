"""add_wasi_integration_to_agent

Migración no destructiva que agrega las columnas de integración Wasi.co
a la tabla agents existente sin borrar datos.

Revision ID: c8d9e0f1a2b3
Revises: 6d298fe98456
Create Date: 2026-09-09 16:59:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, Sequence[str], None] = '6d298fe98456'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Agrega columnas de integración Wasi.co a la tabla agents.
    Usa batch_alter_table para compatibilidad con SQLite (desarrollo local).
    """
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('wasi_company_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('wasi_token', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('wasi_connected', sa.Boolean(), nullable=False, server_default='false'))
        batch_op.add_column(sa.Column('wasi_sync_status', sa.String(length=50), nullable=True, server_default='idle'))
        batch_op.add_column(sa.Column('wasi_last_sync_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('wasi_properties_count', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    """Revierte las columnas de integración Wasi.co."""
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.drop_column('wasi_properties_count')
        batch_op.drop_column('wasi_last_sync_at')
        batch_op.drop_column('wasi_sync_status')
        batch_op.drop_column('wasi_connected')
        batch_op.drop_column('wasi_token')
        batch_op.drop_column('wasi_company_id')
