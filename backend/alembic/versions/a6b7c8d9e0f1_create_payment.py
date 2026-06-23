"""create payment table (cobros Bre-B)

Revision ID: a6b7c8d9e0f1
Revises: f5e6a7b8c9d0
Create Date: 2026-06-24 10:00:00.000000

Crea la tabla `payment` para los cobros Bre-B verificados por vision (Gemini),
que sustituye el flujo de billing de Stripe. La idempotencia se garantiza con un
indice unico (tenant_id, reference). El `downgrade()` elimina la tabla completa.

Feature: genia-agent-platform (Tarea 9.x - Cobros Bre-B)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a6b7c8d9e0f1"
down_revision: Union[str, Sequence[str], None] = "f5e6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea la tabla `payment` y su indice unico (tenant_id, reference)."""
    op.create_table(
        "payment",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reference", sa.String(length=255), nullable=False),
        sa.Column("expected_amount", sa.Integer(), nullable=False),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
            server_default="COP",
        ),
        sa.Column("llave_destino", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("comprobante_ref", sa.String(length=255), nullable=True),
        sa.Column("extracted", sa.JSON(), nullable=True),
        sa.Column("reject_reason", sa.String(length=512), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_payment_tenant_id", "payment", ["tenant_id"])
    op.create_unique_constraint(
        "uq_payment_tenant_reference", "payment", ["tenant_id", "reference"]
    )


def downgrade() -> None:
    """Elimina la tabla `payment` y sus indices/constraints."""
    op.drop_constraint("uq_payment_tenant_reference", "payment", type_="unique")
    op.drop_index("ix_payment_tenant_id", table_name="payment")
    op.drop_table("payment")