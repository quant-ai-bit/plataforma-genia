"""Modelo de Contacto Precargado (base de datos privada del cliente por agente)."""

import uuid
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class PreloadedContact(Base):
    """Contacto precargado masivamente (CSV/Excel) asignado en privado a un agente."""

    __tablename__ = "preloaded_contacts"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    notes = Column(String(500), nullable=True)
    custom_data = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # --- Diagnóstico WhatsApp & IA (Campos Opcionales) ---
    source = Column(String(20), default="manual", nullable=True)  # csv, whatsapp, manual, auto_lead
    nickname = Column(String(100), nullable=True)  # "Don Carlos", "Cami"
    ai_category = Column(String(50), nullable=True)  # cliente_potencial, cliente_existente, aliado_estrategico, personal, proveedor, irrelevante
    ai_confidence = Column(Float, nullable=True)  # 0.0 - 1.0
    ai_analysis = Column(JSON, nullable=True)  # Resultado estructurado del análisis IA
    whatsapp_chat_id = Column(String(100), nullable=True)
    last_message_preview = Column(String(500), nullable=True)
    last_interaction_at = Column(DateTime(timezone=True), nullable=True)

    # Relación
    agent = relationship("Agent", backref="preloaded_contacts")

