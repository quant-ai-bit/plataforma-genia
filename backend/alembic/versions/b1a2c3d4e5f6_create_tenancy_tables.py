"""create tenancy tables (tenant, api_key, subscription) + seed con-tranqui

Revision ID: b1a2c3d4e5f6
Revises: 1532945af24e
Create Date: 2026-06-10 10:00:00.000000

Feature: genia-agent-platform (Tarea 1.1)
"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1a2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "1532945af24e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CON_TRANQUI_SLUG = "con-tranqui"


def upgrade() -> None:
    """Crea las tablas base de tenancy y siembra el tenant con-tranqui."""
    op.create_table(
        "tenant",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("tenant", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_tenant_slug"), ["slug"], unique=True)

    op.create_table(
        "api_key",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("prefix", sa.String(length=20), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("api_key", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_api_key_tenant_id"), ["tenant_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_api_key_key_hash"), ["key_hash"], unique=True
        )

    op.create_table(
        "subscription",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("plan", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("subscription", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_subscription_tenant_id"), ["tenant_id"], unique=True
        )

    # --- Seed idempotente del tenant con-tranqui ---
    bind = op.get_bind()
    existing = bind.execute(
        sa.text("SELECT id FROM tenant WHERE slug = :slug"),
        {"slug": CON_TRANQUI_SLUG},
    ).fetchone()
    if existing is None:
        tenant_table = sa.table(
            "tenant",
            sa.column("id", sa.String),
            sa.column("name", sa.String),
            sa.column("slug", sa.String),
            sa.column("is_active", sa.Boolean),
            sa.column("created_at", sa.DateTime),
        )
        op.bulk_insert(
            tenant_table,
            [
                {
                    "id": uuid.uuid4().hex,
                    "name": CON_TRANQUI_SLUG,
                    "slug": CON_TRANQUI_SLUG,
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc),
                }
            ],
        )


def downgrade() -> None:
    """Elimina las tablas de tenancy (y el tenant sembrado)."""
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM tenant WHERE slug = :slug"),
        {"slug": CON_TRANQUI_SLUG},
    )
    with op.batch_alter_table("subscription", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_subscription_tenant_id"))
    op.drop_table("subscription")
    with op.batch_alter_table("api_key", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_api_key_key_hash"))
        batch_op.drop_index(batch_op.f("ix_api_key_tenant_id"))
    op.drop_table("api_key")
    with op.batch_alter_table("tenant", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_tenant_slug"))
    op.drop_table("tenant")
