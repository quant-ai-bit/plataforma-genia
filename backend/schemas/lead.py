"""
Esquemas Pydantic v2 para el recurso Lead.

Define los modelos de validación para serializar leads capturados
automáticamente por los agentes durante las conversaciones.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class LeadStatusUpdate(BaseModel):
    """Esquema para actualizar el estado CRM de un lead."""
    status: str = Field(..., description="Nuevo estado CRM del lead (primer_contacto, en_cualificacion, cualificado, objetivo_cumplido, perdido)")


class LeadResponse(BaseModel):
    """Representación completa de un lead capturado."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    agent_name: str | None = None
    conversation_id: str | None = None
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    custom_data: dict | None = Field(
        default=None,
        description="Datos personalizados capturados según los custom_fields del agente",
    )
    source_channel: str = Field(..., description="Canal de origen: web, whatsapp, telegram, etc.")
    status: str | None = Field(default="primer_contacto", description="Estado en el pipeline CRM")
    captured_at: datetime
    updated_at: datetime | None = None
