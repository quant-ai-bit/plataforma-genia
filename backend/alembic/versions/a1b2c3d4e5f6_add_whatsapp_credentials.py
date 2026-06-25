"""add whatsapp credentials to agents

Revision ID: a1b2c3d4e5f6
Revises: f5e6a7b8c9d0
Create Date: 2026-06-23

Añade columnas de credenciales de WhatsApp Cloud API al modelo Agent para
soportar integración multi-línea por agente (cada cliente conecta su propia
línea de WhatsApp Business).
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "f5e6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite requiere batch mode para ALTER TABLE
    with op.batch_alter_table("agents", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "whatsapp_phone_number_id",
                sa.String(100),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "whatsapp_access_token",
                sa.Text(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "whatsapp_app_secret",
                sa.Text(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "whatsapp_verify_token",
                sa.String(255),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "whatsapp_connected",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch_op.create_index(
            "ix_agents_whatsapp_phone_number_id",
            ["whatsapp_phone_number_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("agents", schema=None) as batch_op:
        batch_op.drop_index("ix_agents_whatsapp_phone_number_id")
        batch_op.drop_column("whatsapp_connected")
        batch_op.drop_column("whatsapp_verify_token")
        batch_op.drop_column("whatsapp_app_secret")
        batch_op.drop_column("whatsapp_access_token")
        batch_op.drop_column("whatsapp_phone_number_id")
