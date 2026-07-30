"""
Esquemas Pydantic v2 para Contactos Precargados.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PreloadedContactCreate(BaseModel):
    name: str = Field(..., max_length=255)
    phone: str = Field(..., max_length=50)
    email: str | None = None
    notes: str | None = None
    custom_data: dict | None = None


class PreloadedContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    name: str
    phone: str
    email: str | None = None
    notes: str | None = None
    custom_data: dict | None = None
    created_at: datetime
