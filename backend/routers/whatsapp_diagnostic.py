"""
Router REST para Diagnóstico WhatsApp + IA y Seguimiento Outbound en PLATAFORMA GENIA.
"""

import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.agent import Agent
from services.auth_service import get_current_user
from services.whatsapp_diagnostic_service import (
    fetch_whatsapp_contacts,
    fetch_chat_messages,
    run_diagnostic,
    import_analyzed_contacts_to_db,
    create_leads_from_diagnostic_results,
    diagnostic_progress_store,
)
from services.whatsapp_outbound_service import (
    suggest_followup_message,
    send_single_outbound,
    send_batch_outbound,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["WhatsApp Diagnostic & Outbound"])


# ── Esquemas Pydantic ──

class BusinessContextSchema(BaseModel):
    business_name: str = Field(..., description="Nombre del negocio (OBLIGATORIO)")
    business_type: str = Field(..., description="Tipo de negocio / Industria (OBLIGATORIO)")
    products_services: Optional[str] = Field(None, description="Productos o servicios ofrecidos (Opcional)")
    ideal_client: Optional[str] = Field(None, description="Perfil de cliente ideal (Opcional)")
    sale_keywords: Optional[List[str]] = Field(default=[], description="Palabras clave de venta (Opcional)")
    personal_keywords: Optional[List[str]] = Field(default=[], description="Palabras clave personales (Opcional)")
    additional_notes: Optional[str] = Field(None, description="Notas adicionales de contexto (Opcional)")


class DiagnosticRunRequest(BaseModel):
    selected_chat_ids: Optional[List[str]] = Field(default=None, description="IDs de chats en modo manual")
    limit: Optional[int] = Field(default=50, description="Límite de chats en modo automático")
    days_back: Optional[int] = Field(default=30, description="Rango de días en modo automático")


class DiagnosticImportRequest(BaseModel):
    results: List[Dict[str, Any]] = Field(..., description="Resultados del diagnóstico analizado")


class DiagnosticPipelineRequest(BaseModel):
    results: List[Dict[str, Any]] = Field(..., description="Resultados del diagnóstico analizado")


class OutboundSuggestRequest(BaseModel):
    phone: str = Field(..., description="Teléfono del destinatario")
    custom_instruction: Optional[str] = Field(None, description="Instrucciones adicionales para la IA")


class OutboundSendRequest(BaseModel):
    phone: str = Field(..., description="Teléfono del destinatario")
    message: str = Field(..., description="Mensaje a enviar")


class OutboundBatchSendRequest(BaseModel):
    items: List[OutboundSendRequest] = Field(..., description="Lista de envíos (máximo 5 por lote)")


# ── Endpoints Contexto de Negocio ──

@router.get("/{agent_id}/diagnostic/context")
def get_business_context(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Obtiene el contexto de negocio del agente para el diagnóstico."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado.")

    context = getattr(agent, "diagnostic_business_context", None) or {}
    return {
        "agent_id": agent_id,
        "context": context,
        "last_run_at": agent.diagnostic_last_run_at,
        "status": agent.diagnostic_status or "idle",
    }


@router.put("/{agent_id}/diagnostic/context")
def update_business_context(
    agent_id: str,
    payload: BusinessContextSchema,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Guarda o edita el contexto de negocio del agente (2 campos obligatorios, 5 opcionales)."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado.")

    if not payload.business_name.strip() or not payload.business_type.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nombre del negocio y Tipo de negocio son obligatorios.",
        )

    ctx_dict = payload.model_dump()
    agent.diagnostic_business_context = ctx_dict
    db.commit()

    logger.info(f"[DIAGNOSTIC CONTEXT] Contexto de negocio actualizado para el agente {agent_id}.")
    return {"status": "success", "message": "Contexto de negocio guardado correctamente.", "context": ctx_dict}


# ── Endpoints de Contactos & Chats ──

@router.get("/{agent_id}/whatsapp/contacts")
async def get_whatsapp_contacts(
    agent_id: str,
    limit: int = 50,
    days: int = 90,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Obtiene la lista de contactos/chats desde la base local de WAHA (riesgo nulo).
    Permite filtrar por número de chats y por rango de días.
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado.")

    session_name = agent.whatsapp_qr_instance_name or f"genia_{agent_id[:8]}"
    contacts = await fetch_whatsapp_contacts(session_name, limit=limit, days_back=days)
    return {"status": "success", "count": len(contacts), "contacts": contacts}


@router.get("/{agent_id}/whatsapp/contacts/{chat_id:path}/messages")
async def get_chat_messages(
    agent_id: str,
    chat_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Obtiene el historial completo de mensajes de un chat específico."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado.")

    session_name = agent.whatsapp_qr_instance_name or f"genia_{agent_id[:8]}"
    messages = await fetch_chat_messages(session_name, chat_id, limit=limit)
    return {"status": "success", "chat_id": chat_id, "count": len(messages), "messages": messages}


# ── Endpoints de Diagnóstico ──

@router.post("/{agent_id}/diagnostic/run")
async def run_whatsapp_diagnostic(
    agent_id: str,
    payload: DiagnosticRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Inicia el diagnóstico de WhatsApp (Manual o Automático) en segundo plano con throttling seguro.
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado.")

    agent.diagnostic_status = "running"
    db.commit()

    # Ejecutar diagnóstico
    res = await run_diagnostic(
        agent=agent,
        db=db,
        selected_chat_ids=payload.selected_chat_ids,
        limit=payload.limit or 50,
        days_back=payload.days_back or 30,
    )
    return {"status": "started", "diagnostic_state": res}


@router.get("/{agent_id}/diagnostic/status")
def get_diagnostic_status(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Obtiene el estado en tiempo real y progreso (%) del diagnóstico del agente."""
    state = diagnostic_progress_store.get(agent_id)
    if not state:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        state = {
            "status": getattr(agent, "diagnostic_status", "idle") or "idle",
            "progress": 100 if getattr(agent, "diagnostic_status", "") == "completed" else 0,
            "current_chat": "Listo",
            "total_chats": 0,
            "analyzed_chats": 0,
            "estimated_remaining_seconds": 0,
            "results": [],
        }
    return state


@router.post("/{agent_id}/diagnostic/import")
def import_diagnostic_contacts(
    agent_id: str,
    payload: DiagnosticImportRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Importa contactos analizados a PreloadedContacts (fusión inteligente)."""
    res = import_analyzed_contacts_to_db(agent_id, payload.results, db)
    return res


@router.post("/{agent_id}/diagnostic/pipeline")
def create_pipeline_leads(
    agent_id: str,
    payload: DiagnosticPipelineRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Crea automáticamente leads en el CRM Kanban a partir del diagnóstico."""
    res = create_leads_from_diagnostic_results(agent_id, payload.results, db)
    return res


# ── Endpoints Outbound (Seguimiento 1 a 1 y Lote) ──

@router.post("/{agent_id}/outbound/suggest")
async def suggest_outbound_followup(
    agent_id: str,
    payload: OutboundSuggestRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Genera una sugerencia de mensaje de seguimiento redactada por IA."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado.")

    res = await suggest_followup_message(
        agent=agent,
        phone=payload.phone,
        db=db,
        custom_instruction=payload.custom_instruction,
    )
    return res


@router.post("/{agent_id}/outbound/send")
async def send_outbound_message(
    agent_id: str,
    payload: OutboundSendRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Envía un mensaje outbound individual con presencia de escritura simulada."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado.")

    res = await send_single_outbound(
        agent=agent,
        phone=payload.phone,
        message_text=payload.message,
        db=db,
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@router.post("/{agent_id}/outbound/send-batch")
async def send_outbound_batch_messages(
    agent_id: str,
    payload: OutboundBatchSendRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Envía un lote pequeño (máximo 5) con retardos de 2 a 4 minutos entre envíos."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado.")

    items_dict = [item.model_dump() for item in payload.items]
    res = await send_batch_outbound(agent=agent, items=items_dict, db=db)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res
