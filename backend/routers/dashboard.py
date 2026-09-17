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
from services.auth_service import get_current_user
from routers.users import get_user_role_and_account

router = APIRouter(prefix="/dashboard", tags=["Dashboard Analytics"])


@router.get("/metrics")
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Retorna métricas consolidadas sobre el estado de la plataforma.
    Para administradores, muestra métricas globales agregadas.
    Para usuarios estándar (rol 'user'), filtra todas las métricas exclusivamente
    al agente de IA asignado a su cuenta.
    """
    is_admin, user_acc = get_user_role_and_account(db, current_user)
    agent_id_filter = None

    if not is_admin:
        if not user_acc or not user_acc.assigned_agent_id:
            return {
                "total_agents": 0,
                "total_conversations": 0,
                "total_leads": 0,
                "conversations_by_status": {"active": 0, "closed": 0, "handoff": 0},
                "conversations_by_channel": {},
                "leads_by_channel": {},
                "leads_history": [],
                "recent_leads": [],
                "recent_conversations": [],
                "messages_per_agent": {},
            }
        agent_id_filter = user_acc.assigned_agent_id

    # ── Conteo general de entidades ──────────────────────────────────
    if agent_id_filter:
        total_agents = 1
        total_conversations = (
            db.query(func.count(Conversation.id))
            .filter(Conversation.agent_id == agent_id_filter)
            .scalar() or 0
        )
        total_leads = (
            db.query(func.count(Lead.id))
            .filter(Lead.agent_id == agent_id_filter)
            .scalar() or 0
        )
    else:
        total_agents = db.query(func.count(Agent.id)).scalar() or 0
        total_conversations = db.query(func.count(Conversation.id)).scalar() or 0
        total_leads = db.query(func.count(Lead.id)).scalar() or 0

    # ── Conversaciones por estado ───────────────────────────────────
    conv_status_q = db.query(Conversation.status, func.count(Conversation.id))
    if agent_id_filter:
        conv_status_q = conv_status_q.filter(Conversation.agent_id == agent_id_filter)
    status_counts = conv_status_q.group_by(Conversation.status).all()

    conversations_by_status = {
        "active": 0,
        "closed": 0,
        "handoff": 0,
    }
    for stat, count in status_counts:
        conversations_by_status[stat] = count

    # ── Conversaciones por canal ────────────────────────────────────
    conv_chan_q = db.query(Conversation.channel, func.count(Conversation.id))
    if agent_id_filter:
        conv_chan_q = conv_chan_q.filter(Conversation.agent_id == agent_id_filter)
    channel_counts = conv_chan_q.group_by(Conversation.channel).all()

    conversations_by_channel = {}
    for chan, count in channel_counts:
        conversations_by_channel[chan or "desconocido"] = count

    # ── Leads por canal de origen ───────────────────────────────────
    lead_chan_q = db.query(Lead.source_channel, func.count(Lead.id))
    if agent_id_filter:
        lead_chan_q = lead_chan_q.filter(Lead.agent_id == agent_id_filter)
    lead_channel_counts = lead_chan_q.group_by(Lead.source_channel).all()

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
    recent_leads_query_builder = (
        db.query(func.date(Lead.captured_at).label("day"), func.count(Lead.id))
        .filter(Lead.captured_at >= start_date)
    )
    if agent_id_filter:
        recent_leads_query_builder = recent_leads_query_builder.filter(Lead.agent_id == agent_id_filter)
    recent_leads_query = recent_leads_query_builder.group_by(func.date(Lead.captured_at)).all()

    for day_obj, count in recent_leads_query:
        day_str = day_obj if isinstance(day_obj, str) else day_obj.isoformat()
        if day_str in leads_last_7_days:
            leads_last_7_days[day_str] = count

    # Convertir a una lista de diccionarios ordenada para gráficas
    leads_history = [
        {"date": date, "leads": count} for date, count in leads_last_7_days.items()
    ]

    # ── Leads recientes (últimos 5) ───────────────────────────────
    recent_leads = []
    leads_q = db.query(Lead)
    if agent_id_filter:
        leads_q = leads_q.filter(Lead.agent_id == agent_id_filter)
    db_recent_leads = leads_q.order_by(Lead.captured_at.desc()).limit(5).all()

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
    convs_q = db.query(Conversation)
    if agent_id_filter:
        convs_q = convs_q.filter(Conversation.agent_id == agent_id_filter)
    db_recent_convs = convs_q.order_by(Conversation.last_message_at.desc()).limit(5).all()

    for conv in db_recent_convs:
        last_msg_text = ""
        if conv.messages:
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
    msg_q = (
        db.query(Conversation.agent_id, func.count(Message.id))
        .join(Message, Message.conversation_id == Conversation.id)
    )
    if agent_id_filter:
        msg_q = msg_q.filter(Conversation.agent_id == agent_id_filter)
    messages_per_agent_query = msg_q.group_by(Conversation.agent_id).all()

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
