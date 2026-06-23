"""Modelo de Lead (cliente potencial)."""

import uuid

from sqlalchemy import Column, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Lead(Base):
    """Lead capturado automáticamente durante una conversación."""

    __tablename__ = "leads"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)
    name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    custom_data = Column(JSON, default=dict)  # Campos dinámicos capturados
    source_channel = Column(String(20), default="web")
    captured_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relaciones
    agent = relationship("Agent", back_populates="leads")
    conversation = relationship("Conversation", back_populates="lead")

