"""
provisioning_service: aprovisionamiento idempotente de tenants (Component 7).

Define el `Provisioning_Service` que crea/actualiza por completo un tenant de
GENIA a partir de una especificacion declarativa (`TenantSpec`). Es la unica
logica de aprovisionamiento, invocada de forma equivalente por las TRES vias:
- script de seed (`backend/scripts/seed_tenant.py`),
- endpoint admin (`POST /v1/admin/tenants`),
- migracion Alembic de datos (`seed_con_tranqui`).

`provision(spec, db)` es idempotente (clave: `tenant.slug`):
1. `tenant_service.upsert_by_slug`  -> crea/actualiza el tenant.
2. `apikey_service.issue`           -> emite API key (hash; secreto una sola vez;
   no re-emite en re-ejecuciones salvo rotacion explicita).
3. `agent_service.upsert`           -> Agent_Config (system_prompt + Gemini/Vertex
   + model_params + enabled_mcp_tools).
4. `mcp_registry.register_remote`   -> apuntador al MCP remoto (URL/token por env)
   + catalogo de herramientas habilitadas.
5. `billing_service.ensure_subscription` -> suscripcion mensual del tenant.
6. `knowledge_service.ensure_collection` -> coleccion ChromaDB del tenant (RAG).

Todo queda acotado a `tenant_id` (Requisito 7.3). Los secretos (token de
servicio MCP, datos de cobro Bre-B, credenciales) NUNCA viven en codigo: solo se
registran NOMBRES de variables de entorno, resueltas desde `Settings`/entorno.

Feature: genia-agent-platform (Tareas 14.1, 14.3)
"""

import logging
import os
import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from config import settings
from services import agent_service, apikey_service, billing_service, tenant_service
from services import knowledge_service
from services.mcp_registry import mcp_registry

logger = logging.getLogger(__name__)

_PLACEHOLDER_RE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")


def _resolve_placeholder(value: str | None) -> str | None:
    """
    Resuelve un valor `${ENV_VAR}` contra `Settings`/entorno.

    Si `value` tiene la forma `${NOMBRE}`, devuelve el valor de la variable de
    entorno correspondiente (preferentemente desde `Settings`); en otro caso
    devuelve `value` sin cambios. Permite que las specs declarativas (YAML)
    referencien variables de entorno sin incrustar secretos ni configuracion.
    """
    if not value:
        return value
    match = _PLACEHOLDER_RE.match(value.strip())
    if not match:
        return value
    name = match.group(1)
    resolved = getattr(settings, name.lower(), None) or os.getenv(name)
    return resolved or value


@dataclass
class TenantSpec:
    """Especificacion declarativa para aprovisionar un tenant."""

    name: str
    slug: str
    system_prompt: str
    model: str | None = None
    model_params: dict = field(default_factory=dict)
    enabled_mcp_tools: list[str] = field(default_factory=list)
    mcp_server_url_env: str | None = None
    mcp_service_token_env: str | None = None
    subscription_plan: str | None = None
    knowledge_collection: str | None = None


@dataclass
class ProvisioningResult:
    """Resultado del aprovisionamiento de un tenant."""

    tenant: object
    api_secret: str | None
    agent: object
    subscription: object
    knowledge_collection: str | None
    mcp_config: object | None = None

    def to_public_dict(self) -> dict:
        """
        Serializa el resultado para una respuesta de API.

        Incluye el `api_secret` SOLO si se emitio en esta ejecucion (una unica
        vez). En re-ejecuciones sin rotacion, `api_secret` es `null`.
        """
        return {
            "tenant_id": getattr(self.tenant, "id", None),
            "slug": getattr(self.tenant, "slug", None),
            "agent_id": getattr(self.agent, "id", None),
            "subscription_status": getattr(self.subscription, "status", None),
            "subscription_plan": getattr(self.subscription, "plan", None),
            "knowledge_collection": self.knowledge_collection,
            "mcp_config_id": getattr(self.mcp_config, "id", None),
            "api_key": self.api_secret,
            "api_key_issued": self.api_secret is not None,
        }


class ProvisioningService:
    """Orquestador idempotente del aprovisionamiento de tenants."""

    async def provision(
        self, spec: TenantSpec, db: Session, rotate_api_key: bool = False
    ) -> ProvisioningResult:
        """
        Aprovisiona (idempotente) un tenant completo a partir de `spec`.

        Args:
            spec: Especificacion declarativa del tenant.
            db: Sesion de base de datos.
            rotate_api_key: Si True, rota (re-emite) la API key del tenant.

        Returns:
            `ProvisioningResult` con el tenant, agente, suscripcion, coleccion de
            conocimiento y el secreto de la API key (solo si se emitio ahora).
        """
        # 1. Tenant (idempotente por slug).
        tenant = tenant_service.upsert_by_slug(db, spec.name, spec.slug)

        # 2. API key (no re-emite salvo rotacion explicita).
        api_secret, _api_key = apikey_service.issue(
            db, tenant.id, rotate=rotate_api_key
        )

        # 3. Agent_Config (system_prompt + Gemini/Vertex + tools habilitadas).
        model = _resolve_placeholder(spec.model) or settings.vertex_gemini_model
        agent = agent_service.upsert(
            db,
            tenant_id=tenant.id,
            system_prompt=spec.system_prompt,
            model=model,
            model_params=spec.model_params,
            enabled_mcp_tools=spec.enabled_mcp_tools,
            provider="vertex",
            name=spec.name,
        )

        # 4. Apuntador al MCP remoto (solo nombres de env vars; sin secretos).
        mcp_config = None
        if spec.mcp_server_url_env and spec.mcp_service_token_env:
            mcp_config = await mcp_registry.register_remote(
                db,
                tenant_id=tenant.id,
                url_env=spec.mcp_server_url_env,
                service_token_env=spec.mcp_service_token_env,
                tools=spec.enabled_mcp_tools,
                name=f"{spec.slug}-mcp-remoto",
            )

        # 5. Suscripcion mensual del tenant (idempotente).
        plan = _resolve_placeholder(spec.subscription_plan)
        subscription = billing_service.ensure_subscription(db, tenant.id, plan=plan)

        # 6. Coleccion ChromaDB del tenant para el RAG (idempotente).
        collection = knowledge_service.ensure_collection(
            db, tenant.id, spec.knowledge_collection
        )

        logger.info(
            "Aprovisionamiento completado para tenant %s (slug=%s, api_key_emitida=%s)",
            tenant.id,
            tenant.slug,
            api_secret is not None,
        )
        return ProvisioningResult(
            tenant=tenant,
            api_secret=api_secret,
            agent=agent,
            subscription=subscription,
            knowledge_collection=collection,
            mcp_config=mcp_config,
        )
