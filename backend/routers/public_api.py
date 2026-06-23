"""
Router publico `/v1` de PLATAFORMA GENIA (API agente-como-servicio).

Expone la API B2B multi-tenant, separada de los routers internos del dashboard.
La autenticacion es por API key (cabecera `X-API-Key`) mediante las dependencias
`require_tenant` / `enforce_subscription`, que ademas resuelven el Tenant y
aplican enforcement de suscripcion y limite de uso.

Endpoints:
- GET  /v1/health                         -> liveness, sin auth (5.1)
- POST /v1/agent/chat                      -> conversacion con el agente (5.2)
- GET  /v1/agent/conversations/{id}        -> historial del tenant (5.3)

Todo el procesamiento usa el `Agent_Config`, `Knowledge_Base` y `MCP_Tools` del
tenant resuelto, pasando `tenant_id` a Model_Service / RAG / MCP. Cada solicitud
autenticada y procesada registra exactamente un Usage_Record.

Feature: genia-agent-platform (Tareas 5.1, 5.2, 5.3)
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.conversation import Conversation, Message
from models.tenant import Tenant
from services import agent_service, breb_payment_service, export_service, mcp_service
from services.ai_service import generate_via_model_service
from services.auth_service import get_current_user
from services.knowledge_service import retrieve_context_for_tenant
from services.model_service import AgentUsageRecorder
from services.providers.base import ModelUnavailableError
from services.security.api_key_dep import enforce_subscription, require_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["API Publica v1"])


# ── Esquemas de request/response ─────────────────────────────────────
class ChatRequest(BaseModel):
    """Cuerpo de la solicitud de `POST /v1/agent/chat`."""

    conversation_id: str | None = Field(
        default=None, description="ID de conversacion existente o null para crear una nueva"
    )
    message: str = Field(..., description="Mensaje del usuario")
    metadata: dict = Field(default_factory=dict, description="Metadatos opcionales (canal, etc.)")


class ActionResult(BaseModel):
    """Resultado de una accion MCP ejecutada durante la conversacion."""

    tool: str
    status: str
    summary: str


class UsageInfoOut(BaseModel):
    """Metadatos de consumo de la solicitud."""

    input_tokens: int = 0
    output_tokens: int = 0
    provider: str | None = None


class ChatResponse(BaseModel):
    """Respuesta de `POST /v1/agent/chat`."""

    conversation_id: str
    reply: str
    actions: list[ActionResult] = Field(default_factory=list)
    usage: UsageInfoOut


# ── Utilidades internas ──────────────────────────────────────────────
def _normalize_tool_call(tc) -> tuple[str | None, dict]:
    """Normaliza un tool_call de cualquier proveedor a (nombre, argumentos)."""
    if not isinstance(tc, dict):
        return None, {}
    fn = tc.get("function") or {}
    name = fn.get("name") or tc.get("name")
    raw_args = fn.get("arguments") if "arguments" in fn else tc.get("arguments")
    if isinstance(raw_args, str):
        try:
            args = json.loads(raw_args) if raw_args else {}
        except json.JSONDecodeError:
            args = {}
    elif isinstance(raw_args, dict):
        args = raw_args
    else:
        args = {}
    return name, args


def _conversation_in_tenant(db: Session, conversation: Conversation, tenant_id: str) -> bool:
    """Verifica que la conversacion pertenezca al tenant (via su agente)."""
    from models.agent import Agent

    agent = db.query(Agent).filter(Agent.id == conversation.agent_id).first()
    return bool(agent is not None and agent.tenant_id == tenant_id)


# ── Endpoints ────────────────────────────────────────────────────────
@router.get("/health", tags=["Health"])
async def health():
    """Liveness de la API publica `/v1` (sin autenticacion)."""
    return {"status": "ok", "service": "genia-public-api", "version": "v1"}


@router.post("/agent/chat", response_model=ChatResponse)
async def agent_chat(
    body: ChatRequest,
    tenant: Tenant = Depends(enforce_subscription),
    db: Session = Depends(get_db),
):
    """
    Procesa un turno de conversacion del agente del tenant.

    Resuelve el Agent_Config del tenant, recupera contexto RAG del tenant,
    genera la respuesta via Model_Service (Vertex -> Groq -> OpenRouter) y
    ejecuta las MCP_Tools habilitadas. Crea exactamente un Usage_Record por
    solicitud autenticada y procesada.
    """
    agent = agent_service.get_for_tenant(db, tenant.id)
    if agent is None:
        raise HTTPException(status_code=404, detail="El tenant no tiene un Agent_Config configurado")

    # Resolver o crear la conversacion (acotada al tenant).
    if body.conversation_id:
        conversation = (
            db.query(Conversation).filter(Conversation.id == body.conversation_id).first()
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversacion no encontrada")
        if not _conversation_in_tenant(db, conversation, tenant.id):
            raise HTTPException(status_code=403, detail="La conversacion pertenece a otro tenant")
    else:
        conversation = Conversation(
            agent_id=agent.id,
            channel=(body.metadata or {}).get("channel", "web"),
            status="active",
        )
        db.add(conversation)
        db.flush()

    # Persistir el mensaje del usuario.
    user_msg = Message(conversation_id=conversation.id, role="user", content=body.message)
    db.add(user_msg)
    db.flush()

    # Historial previo (excluye el mensaje recien agregado).
    history_rows = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.sent_at.asc())
        .all()
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in history_rows
        if m.id != user_msg.id
    ]

    # RAG acotado al tenant (vacio si no hay Knowledge_Base -> prompt + modelo).
    knowledge_context = retrieve_context_for_tenant(tenant.id, body.message, db=db)

    system_prompt = agent.system_prompt or ""
    if knowledge_context:
        system_prompt += (
            "\n\n[CONTEXTO DE CONOCIMIENTO - usa esta informacion para responder:]\n"
            f"{knowledge_context}"
        )

    messages = list(history)
    messages.append({"role": "user", "content": body.message})

    # Herramientas del tenant: built-in + MCP_Tools habilitadas en el Agent_Config.
    tools = None
    try:
        from services.mcp_builtin_server import is_builtin_tool
        from services.mcp_registry import mcp_registry

        fc_tools, _origin = await mcp_registry.get_tools_for_agent(
            db=db, agent_id=agent.id, custom_fields=agent.custom_fields
        )
        enabled = set(agent.enabled_mcp_tools or [])
        filtered = [
            t
            for t in fc_tools
            if is_builtin_tool(t["function"]["name"]) or t["function"]["name"] in enabled
        ]
        tools = filtered or None
    except Exception as exc:  # noqa: BLE001 - las tools son best-effort
        logger.warning("No se pudieron cargar las MCP_Tools del tenant %s: %s", tenant.id, exc)
        tools = None

    # Generacion via Model_Service con registro de Usage_Record (exactamente uno).
    usage_ctx = AgentUsageRecorder(db=db, agent_id=agent.id, tenant_id=tenant.id)
    try:
        result = await generate_via_model_service(
            messages=messages,
            system_prompt=system_prompt,
            tools=tools,
            max_tokens=agent.max_tokens,
            temperature=agent.temperature,
            usage_ctx=usage_ctx,
        )
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Servicio de modelo no disponible: {exc.detail}")

    # Ejecutar MCP_Tools solicitadas por el modelo (auditado por tenant).
    actions: list[ActionResult] = []
    for tc in result.tool_calls or []:
        tool_name, args = _normalize_tool_call(tc)
        if not tool_name:
            continue
        tool_result = await mcp_service.invoke(
            db=db,
            tenant=tenant,
            tool_name=tool_name,
            params=args,
            agent=agent,
            model_provider=result.provider_name,
            metadata=body.metadata,
        )
        actions.append(
            ActionResult(
                tool=tool_name,
                status=tool_result.status,
                summary=tool_result.summary(),
            )
        )

    # Persistir la respuesta del asistente.
    assistant_msg = Message(
        conversation_id=conversation.id, role="assistant", content=result.text or ""
    )
    db.add(assistant_msg)

    from datetime import datetime, timezone

    conversation.last_message_at = datetime.now(timezone.utc)
    db.commit()

    return ChatResponse(
        conversation_id=conversation.id,
        reply=result.text or "",
        actions=actions,
        usage=UsageInfoOut(
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            provider=result.provider_name,
        ),
    )


@router.get("/agent/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    tenant: Tenant = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """
    Recupera el historial de una conversacion del tenant resuelto.

    Devuelve 404 si no existe y 403 si la conversacion pertenece a otro tenant
    (autorizacion cross-tenant, Requisito 7.6).
    """
    conversation = (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversacion no encontrada")
    if not _conversation_in_tenant(db, conversation, tenant.id):
        raise HTTPException(status_code=403, detail="La conversacion pertenece a otro tenant")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.sent_at.asc())
        .all()
    )
    return {
        "conversation_id": conversation.id,
        "status": conversation.status,
        "messages": [
            {"role": m.role, "content": m.content, "sent_at": m.sent_at.isoformat() if m.sent_at else None}
            for m in messages
        ],
    }






# -- Cobros Bre-B: checkout y verificacion por vision --
class CheckoutRequest(BaseModel):
    """Cuerpo opcional de `POST /v1/payments/checkout`."""

    amount: int | None = Field(
        default=None, description="Monto en centavos COP; por defecto el de la suscripcion"
    )
    reference: str | None = Field(
        default=None, description="Referencia del cobro; se genera una si se omite"
    )


class CheckoutResponse(BaseModel):
    """Respuesta de `POST /v1/payments/checkout`."""

    reference: str
    llave: str
    titular: str | None = None
    amount: int
    currency: str
    qr: str = Field(..., description="QR del cobro (imagen base64 data URL o cadena)")
    qr_payload: str = Field(..., description="Cadena BREB|llave|monto|referencia codificada en el QR")


class VerifyRequest(BaseModel):
    """Cuerpo de `POST /v1/payments/verify`."""

    reference: str = Field(..., description="Referencia del cobro a verificar")
    image_base64: str = Field(
        ..., description="Imagen del comprobante en base64 (admite data URL)"
    )


class VerifyResponse(BaseModel):
    """Respuesta de `POST /v1/payments/verify`."""

    status: str
    reason: str | None = None
    extracted: dict | None = None


@router.post("/payments/checkout", response_model=CheckoutResponse, tags=["Cobros"])
async def payments_checkout(
    body: CheckoutRequest,
    tenant: Tenant = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """
    Crea un cobro Bre-B `pending` para el tenant y devuelve los datos del QR.

    Autenticado por API key (`require_tenant`). El cliente renderiza el QR a partir
    de `qr` (imagen base64) o de `qr_payload` (la cadena codificada). La suscripcion se activara
    cuando el comprobante se verifique en `POST /v1/payments/verify`.
    """
    return breb_payment_service.create_checkout(
        db, tenant, amount=body.amount, reference=body.reference
    )


@router.post("/payments/verify", response_model=VerifyResponse, tags=["Cobros"])
async def payments_verify(
    body: VerifyRequest,
    tenant: Tenant = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """
    Verifica el comprobante Bre-B de un cobro del tenant mediante vision (Gemini).

    Autenticado por API key (`require_tenant`). Devuelve 404 si el cobro no existe y
    422 si el comprobante es ilegible. Si los datos coinciden con lo esperado, marca
    el cobro `verified` y activa la `Subscription` del tenant por un mes; si no, lo
    marca `rejected` con el motivo. Si el servicio de vision no tiene
    credenciales, devuelve `pending_manual_review` en vez de fallar.
    """
    return await breb_payment_service.verify_payment(
        db, tenant, reference=body.reference, image_base64=body.image_base64
    )

# ── Observabilidad: Evidence_Export (10.2) ───────────────────────────
@router.get("/admin/evidence-export", tags=["Admin"])
async def evidence_export(
    from_: str = Query(..., alias="from", description="Fecha inicio YYYY-MM-DD"),
    to: str = Query(..., description="Fecha fin YYYY-MM-DD"),
    tenant_id: str | None = Query(default=None, description="Filtra a un tenant"),
    format: str = Query(default="json", pattern="^(csv|json)$"),
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_user),
):
    """
    Exporta la evidencia combinada (Action_Log + Usage_Record) por rango.

    Requiere autenticacion de Administrator. Combina los registros de
    `action_log` y `agent_usages` cuya marca de tiempo cae dentro de
    `[from, to]` y, si se indica `tenant_id`, solo los de ese tenant. Cada
    registro incluye tenant, timestamp, tipo de operacion y proveedor de modelo.
    Formato `json` (por defecto) o `csv`.
    """
    if format == "csv":
        csv_text = export_service.export_csv(db, from_, to, tenant_id)
        filename = f"evidence_{from_}_{to}.csv"
        return PlainTextResponse(
            content=csv_text,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    return export_service.export_json(db, from_, to, tenant_id)


# ── Aprovisionamiento de tenants en caliente (14.5) ──────────────────
class TenantProvisionRequest(BaseModel):
    """Payload declarativo para aprovisionar un tenant via API admin."""

    name: str
    slug: str
    system_prompt: str
    model: str | None = None
    model_params: dict = Field(default_factory=dict)
    enabled_mcp_tools: list[str] = Field(default_factory=list)
    mcp_server_url_env: str | None = None
    mcp_service_token_env: str | None = None
    subscription_plan: str | None = None
    knowledge_collection: str | None = None
    rotate_api_key: bool = False


@router.post("/admin/tenants", tags=["Admin"])
async def provision_tenant(
    body: TenantProvisionRequest,
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_user),
):
    """
    Aprovisiona (idempotente) un tenant en caliente con el payload declarativo.

    Requiere autenticacion de Administrator. Delega en `Provisioning_Service`,
    que es idempotente por `slug`: re-ejecutar no duplica entidades ni re-emite
    la API key salvo `rotate_api_key=true`. Devuelve el secreto de la API key
    una sola vez (null si no se re-emitio).
    """
    from services.provisioning_service import ProvisioningService, TenantSpec

    spec = TenantSpec(
        name=body.name,
        slug=body.slug,
        system_prompt=body.system_prompt,
        model=body.model,
        model_params=body.model_params,
        enabled_mcp_tools=body.enabled_mcp_tools,
        mcp_server_url_env=body.mcp_server_url_env,
        mcp_service_token_env=body.mcp_service_token_env,
        subscription_plan=body.subscription_plan,
        knowledge_collection=body.knowledge_collection,
    )
    result = await ProvisioningService().provision(spec, db, rotate_api_key=body.rotate_api_key)
    db.commit()
    return result.to_public_dict()
