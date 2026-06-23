"""Modelo de documento de base de conocimiento."""

import uuid

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class KnowledgeDocument(Base):
    """Documento cargado a la base de conocimiento de un agente."""

    __tablename__ = "knowledge_documents"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenant.id"), nullable=True, index=True)  # multi-tenant; nullable por compatibilidad
    filename = Column(String(500), nullable=False)
    content_type = Column(String(20), nullable=False)  # text, pdf, url
    raw_content = Column(Text, nullable=True)  # Texto extraído completo
    chunk_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relación
    agent = relationship("Agent", back_populates="knowledge_documents")
