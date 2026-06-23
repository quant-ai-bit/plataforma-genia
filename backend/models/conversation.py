"""Modelos de Conversación y Mensaje."""

import uuid

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Conversation(Base):
    """Conversación entre un contacto y un agente de IA."""

    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    contact_phone = Column(String(50), nullable=True)
    contact_name = Column(String(255), nullable=True)
    channel = Column(String(20), default="web")
    status = Column(String(20), default="active")  # active, closed, handoff
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    lead_notified = Column(Boolean, default=False, nullable=False, doc="Indica si ya se notificó al encargado la captura completa de este lead")

    # Relaciones
    agent = relationship("Agent", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.sent_at")
    lead = relationship("Lead", back_populates="conversation", uselist=False)

    @property
    def message_count(self) -> int:
        """Cantidad total de mensajes en la conversación."""
        return len(self.messages)



class Message(Base):
    """Mensaje individual dentro de una conversación."""

    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    media_url = Column(String(500), nullable=True)
    media_type = Column(String(20), default="text")  # text, audio, image
    whatsapp_message_id = Column(String(255), nullable=True, unique=True, index=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relación
    conversation = relationship("Conversation", back_populates="messages")
