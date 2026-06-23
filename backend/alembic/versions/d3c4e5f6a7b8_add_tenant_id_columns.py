"""add tenant_id a entidades existentes + backfill con-tranqui + enabled_mcp_tools

Revision ID: d3c4e5f6a7b8
Revises: c2b3d4e5f6a7
Create Date: 2026-06-10 10:10:00.000000

Feature: genia-agent-platform (Tarea 1.3)

Nota: tenant_id se anade como nullable para no romper datos existentes.
Se realiza backfill al tenant con-tranqui. En una fase posterior se
promoveria a NOT NULL + FK formal una vez consolidados todos los datos.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d3c4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "c2b3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tablas existentes que reciben tenant_id (nombres reales de la BD)
TENANT_ID_TABLES = [
    "agents",
    "knowledge_documents",
    "knowledge_chunks",
    "agent_usages",
    "mcp_server_configs",
]


def upgrade() -> None:
    """Anade tenant_id (nullable) + enabled_mcp_tools y hace backfill a con-tranqui."""
    for table in TENANT_ID_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column("tenant_id", sa.String(), nullable=True))
            batch_op.create_index(
                batch_op.f(f"ix_{table}_tenant_id"), ["tenant_id"], unique=False
            )

    # enabled_mcp_tools (lista de MCP_Tools habilitadas por tenant) en agents
    with op.batch_alter_table("agents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("enabled_mcp_tools", sa.JSON(), nullable=True))

    # --- Backfill: asociar datos existentes al tenant con-tranqui ---
    bind = op.get_bind()
    row = bind.execute(
        sa.text("SELECT id FROM tenant WHERE slug = :slug"),
        {"slug": "con-tranqui"},
    ).fetchone()
    if row is not None:
        tenant_id = row[0]
        for table in TENANT_ID_TABLES:
            bind.execute(
                sa.text(
                    f"UPDATE {table} SET tenant_id = :tid WHERE tenant_id IS NULL"
                ),
                {"tid": tenant_id},
            )


def downgrade() -> None:
    """Revierte enabled_mcp_tools y tenant_id de las tablas existentes."""
    with op.batch_alter_table("agents", schema=None) as batch_op:
        batch_op.drop_column("enabled_mcp_tools")

    for table in TENANT_ID_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_index(batch_op.f(f"ix_{table}_tenant_id"))
            batch_op.drop_column("tenant_id")
