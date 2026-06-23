"""Esquemas Pydantic v2 para el recurso AgentImage."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AgentImageResponse(BaseModel):
    """Representación de una imagen de la biblioteca del agente."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    filename: str
    description: str | None = Field(None, description="Descripción de la imagen para contextualizar al LLM")
    url: str = Field(..., description="URL absoluta o pública de la imagen")
    uploaded_at: datetime
