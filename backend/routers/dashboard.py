"""
Router de Dashboard para PLATAFORMA GENIA.

Proporciona métricas de alto nivel y resúmenes de rendimiento para el dashboard
frontend (totales de agentes, chats, leads capturados, métricas por canal, etc.).
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.agent import Agent
from models.conversation import Conversation, Message
from models.lead import Lead

router = APIRouter(prefix="/dashboard", tags=["Dashboard Analytics"])


@router.get("/metrics")
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """
    Retorna métricas consolidadas sobre el estado de la plataforma.

    Incluye conteos totales, distribución por estados/canales,
    leads recientes y actividad diaria.
    """
    # ── Conteo general de entidades ──────────────────────────────────
    total_agents = db.query(func.count(Agent.id)).scalar() or 0
    total_conversations = db.query(func.count(Conversation.id)).scalar() or 0
    total_leads = db.query(func.count(Lead.id)).scalar() or 0

    # ── Conversaciones por estado ───────────────────────────────────
    status_counts = (
        db.query(Conversation.status, func.count(Conversation.id))
        .group_by(Conversation.status)
        .all()
    )
    conversations_by_status = {
        "active": 0,
        "closed": 0,
        "handoff": 0,
    }
    for stat, count in status_counts:
        if stat in conversations_by_status:
            conversations_by_status[stat] = count
        else:
            conversations_by_status[stat] = count

    # ── Conversaciones por canal ────────────────────────────────────
    channel_counts = (
        db.query(Conversation.channel, func.count(Conversation.id))
        .group_by(Conversation.channel)
        .all()
    )
    conversations_by_channel = {}
    for chan, count in channel_counts:
        conversations_by_channel[chan or "desconocido"] = count

    # ── Leads por canal de origen ───────────────────────────────────
    lead_channel_counts = (
        db.query(Lead.source_channel, func.count(Lead.id))
        .group_by(Lead.source_channel)
        .all()
    )
    leads_by_channel = {}
    for chan, count in lead_channel_counts:
        leads_by_channel[chan or "desconocido"] = count

    # ── Histórico de leads (últimos 7 días) ──────────────────────────
    today = datetime.now(timezone.utc).date()
    leads_last_7_days = {}
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        leads_last_7_days[day.isoformat()] = 0

    # Query leads captured in the last 7 days
    start_date = datetime.now(timezone.utc) - timedelta(days=7)
    recent_leads_query = (
        db.query(func.date(Lead.captured_at).label("day"), func.count(Lead.id))
        .filter(Lead.captured_at >= start_date)
        .group_by(func.date(Lead.captured_at))
        .all()
    )

    for day_obj, count in recent_leads_query:
        # En SQLite, func.date retorna un string 'YYYY-MM-DD' o un objeto date según driver
        day_str = day_obj if isinstance(day_obj, str) else day_obj.isoformat()
        if day_str in leads_last_7_days:
            leads_last_7_days[day_str] = count

    # Convertir a una lista de diccionarios ordenada para gráficas
    leads_history = [
        {"date": date, "leads": count} for date, count in leads_last_7_days.items()
    ]

    # ── Leads recientes (últimos 5) ───────────────────────────────
    recent_leads = []
    db_recent_leads = (
        db.query(Lead)
        .order_by(Lead.captured_at.desc())
        .limit(5)
        .all()
    )
    for lead in db_recent_leads:
        recent_leads.append(
            {
                "id": lead.id,
                "name": lead.name or "Sin nombre",
                "phone": lead.phone,
                "email": lead.email,
                "source_channel": lead.source_channel,
                "captured_at": lead.captured_at,
                "agent_name": lead.agent.name if lead.agent else "Agente eliminado",
            }
        )

    # ── Conversaciones recientes (últimas 5 activas) ────────────────
    recent_conversations = []
    db_recent_convs = (
        db.query(Conversation)
        .order_by(Conversation.last_message_at.desc())
        .limit(5)
        .all()
    )
    for conv in db_recent_convs:
        # Obtener el último mensaje
        last_msg_text = ""
        if conv.messages:
            # Dado que están ordenadas por sent_at, el último es el final
            last_msg = conv.messages[-1]
            last_msg_text = last_msg.content

        recent_conversations.append(
            {
                "id": conv.id,
                "contact_name": conv.contact_name or "Usuario Web",
                "contact_phone": conv.contact_phone,
                "channel": conv.channel,
                "status": conv.status,
                "last_message": last_msg_text,
                "last_message_at": conv.last_message_at or conv.started_at,
                "agent_name": conv.agent.name if conv.agent else "Agente eliminado",
            }
        )

    # ── Mensajes por agente ───────────────────────────────────────────
    messages_per_agent_query = (
        db.query(Conversation.agent_id, func.count(Message.id))
        .join(Message, Message.conversation_id == Conversation.id)
        .group_by(Conversation.agent_id)
        .all()
    )
    messages_per_agent = {}
    for agent_id, count in messages_per_agent_query:
        messages_per_agent[agent_id] = count

    return {
        "total_agents": total_agents,
        "total_conversations": total_conversations,
        "total_leads": total_leads,
        "conversations_by_status": conversations_by_status,
        "conversations_by_channel": conversations_by_channel,
        "leads_by_channel": leads_by_channel,
        "leads_history": leads_history,
        "recent_leads": recent_leads,
        "recent_conversations": recent_conversations,
        "messages_per_agent": messages_per_agent,
    }
