"""
Esquemas Pydantic v2 para el recurso KnowledgeDocument.

Define los modelos de validación para serializar documentos de la
base de conocimiento asociados a cada agente.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeDocumentResponse(BaseModel):
    """
    Representación resumida de un documento de conocimiento.

    No incluye raw_content para evitar payloads excesivamente grandes
    en los listados.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    filename: str
    content_type: str = Field(..., description="Tipo MIME del documento (text/plain, application/pdf, etc.)")
    chunk_count: int = Field(..., description="Número de chunks generados a partir del documento")
    uploaded_at: datetime


class KnowledgeDocumentDetail(KnowledgeDocumentResponse):
    """
    Representación detallada de un documento de conocimiento.

    Incluye el contenido crudo completo del documento original.
    """

    raw_content: str = Field(..., description="Contenido completo del documento en texto plano")
