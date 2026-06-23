"""Modelo de base de datos para chunks de conocimiento."""

import uuid
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from database import Base
from config import settings

# Determinar el tipo de vector según el motor de base de datos
is_sqlite = "sqlite" in settings.effective_database_url

if is_sqlite:
    from sqlalchemy import Text as SQLiteText
    VectorType = SQLiteText
else:
    from pgvector.sqlalchemy import Vector
    VectorType = Vector(768)  # Gemini text-embedding-004 = 768 dimensiones


class KnowledgeChunk(Base):
    """Chunk de texto individual con su embedding vectorial asociado."""

    __tablename__ = "knowledge_chunks"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    document_id = Column(String, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(String, index=True, nullable=False)
    tenant_id = Column(String, ForeignKey("tenant.id"), index=True, nullable=True)  # multi-tenant; nullable por compatibilidad
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(VectorType, nullable=True)

    # Relación con el documento padre
    document = relationship("KnowledgeDocument", back_populates="chunks")


# Registrar relación inversa en KnowledgeDocument
# Importante: Esto se hace dinámicamente para evitar imports circulares si se prefiere,
# pero como lo definimos aquí, agregamos la relación a KnowledgeDocument.
from models.knowledge import KnowledgeDocument
KnowledgeDocument.chunks = relationship("KnowledgeChunk", order_by=KnowledgeChunk.chunk_index, back_populates="document", cascade="all, delete-orphan")
