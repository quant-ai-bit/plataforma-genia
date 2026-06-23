"""Modelo de base de datos para almacenar métricas de consumo de tokens y costo por agente y modelo."""

import uuid

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from database import Base


class AgentUsage(Base):
    """Registro de consumo acumulado por agente y modelo."""

    __tablename__ = "agent_usages"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenant.id"), nullable=True, index=True)  # multi-tenant; nullable por compatibilidad
    model = Column(String(100), nullable=False)  # Nombre del modelo de IA usado
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    cost = Column(Float, default=0.0, nullable=False)  # Costo acumulado en USD
    last_used = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # --- Campos de proveedor/fallback y agregacion por periodo (Usage_Record) ---
    model_provider = Column(String(50), nullable=True)  # proveedor realmente utilizado
    fallback_reason = Column(String(255), nullable=True)  # motivo del fallback, si aplico
    period = Column(String(20), nullable=True, index=True)  # periodo de facturacion (ej: 2026-06)

    # Relación bidireccional
    agent = relationship("Agent", back_populates="usages")
