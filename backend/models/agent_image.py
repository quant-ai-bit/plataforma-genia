"""Modelo de base de datos para almacenar imágenes del agente."""

import uuid

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class AgentImage(Base):
    """Imagen cargada a la biblioteca de un agente."""

    __tablename__ = "agent_images"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    filename = Column(Text, nullable=False)
    description = Column(Text, nullable=True)  # Descripción para contexto del LLM
    url = Column(Text, nullable=False)  # URL pública o base64 Data URL para acceder a la imagen
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relación bidireccional
    agent = relationship("Agent", back_populates="images")
