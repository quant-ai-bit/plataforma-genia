"""seed con-tranqui tenant via Provisioning_Service (data migration)

Revision ID: f5e6a7b8c9d0
Revises: e4d5f6a7b8c9
Create Date: 2026-06-23 10:00:00.000000

Siembra el primer tenant `con-tranqui` como parte del despliegue inicial,
reutilizando exactamente la misma logica que el script de seed y el endpoint
admin: el `Provisioning_Service`. Idempotente por `slug`. El `downgrade()`
elimina las filas sembradas por el aprovisionamiento (agente, mcp config,
suscripcion y api_keys del tenant), dejando la fila `tenant` a cargo de la
migracion `create_tenancy_tables`.

Feature: genia-agent-platform (Tarea 14.6)
"""
import asyncio
import os
import sys
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session


# revision identifiers, used by Alembic.
revision: str = "f5e6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "e4d5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CON_TRANQUI_SLUG = "con-tranqui"


def _spec_path() -> str:
    """Ruta al YAML declarativo del tenant con-tranqui (relativa al backend)."""
    backend_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    return os.path.join(backend_root, "provisioning", "con-tranqui.yaml")


def upgrade() -> None:
    """Siembra el tenant con-tranqui invocando el Provisioning_Service."""
    # Asegura que el paquete `backend` este en el path para importar servicios.
    backend_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)

    import yaml
    from services.provisioning_service import ProvisioningService, TenantSpec

    with open(_spec_path(), "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    spec = TenantSpec(
        name=data["name"],
        slug=data["slug"],
        system_prompt=data.get("system_prompt", ""),
        model=data.get("model"),
        model_params=data.get("model_params") or {},
        enabled_mcp_tools=data.get("enabled_mcp_tools") or [],
        mcp_server_url_env=data.get("mcp_server_url_env"),
        mcp_service_token_env=data.get("mcp_service_token_env"),
        subscription_plan=data.get("subscription_plan"),
        knowledge_collection=data.get("knowledge_collection"),
    )

    bind = op.get_bind()
    session = Session(bind=bind)
    try:
        asyncio.run(ProvisioningService().provision(spec, session))
        session.flush()
    finally:
        session.close()


def downgrade() -> None:
    """Elimina las filas sembradas por el aprovisionamiento del tenant."""
    bind = op.get_bind()
    row = bind.execute(
        sa.text("SELECT id FROM tenant WHERE slug = :slug"),
        {"slug": CON_TRANQUI_SLUG},
    ).fetchone()
    if row is None:
        return
    tenant_id = row[0]

    # Borrar configs MCP de los agentes del tenant.
    bind.execute(
        sa.text(
            "DELETE FROM mcp_server_configs WHERE agent_id IN "
            "(SELECT id FROM agents WHERE tenant_id = :tid)"
        ),
        {"tid": tenant_id},
    )
    # Borrar agentes, suscripcion y api_keys del tenant.
    bind.execute(sa.text("DELETE FROM agents WHERE tenant_id = :tid"), {"tid": tenant_id})
    bind.execute(
        sa.text("DELETE FROM subscription WHERE tenant_id = :tid"), {"tid": tenant_id}
    )
    bind.execute(
        sa.text("DELETE FROM api_key WHERE tenant_id = :tid"), {"tid": tenant_id}
    )
