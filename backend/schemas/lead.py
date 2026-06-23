"""
Esquemas Pydantic v2 para el recurso Lead.

Define los modelos de validación para serializar leads capturados
automáticamente por los agentes durante las conversaciones.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LeadResponse(BaseModel):
    """Representación completa de un lead capturado."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    conversation_id: str | None = None
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    custom_data: dict | None = Field(
        default=None,
        description="Datos personalizados capturados según los custom_fields del agente",
    )
    source_channel: str = Field(..., description="Canal de origen: web, whatsapp, telegram, etc.")
    captured_at: datetime
