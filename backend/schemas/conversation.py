"""
Esquemas Pydantic v2 para Conversaciones y Mensajes.

Define los modelos de validación para serializar conversaciones,
mensajes individuales y las solicitudes/respuestas del endpoint de chat.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Esquemas de salida – Mensajes
# ---------------------------------------------------------------------------

class MessageResponse(BaseModel):
    """Representación de un mensaje individual dentro de una conversación."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str = Field(..., description="Rol del emisor: user, assistant o system")
    content: str
    media_url: str | None = Field(default=None, description="URL del archivo multimedia adjunto")
    media_type: str | None = Field(default=None, description="Tipo MIME del archivo multimedia")
    sent_at: datetime


# ---------------------------------------------------------------------------
# Esquemas de salida – Conversaciones
# ---------------------------------------------------------------------------

class ConversationResponse(BaseModel):
    """Representación resumida de una conversación para listados."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    contact_phone: str | None = None
    contact_name: str | None = None
    channel: str
    status: str
    started_at: datetime
    last_message_at: datetime | None = None
    message_count: int = 0


class ConversationDetail(ConversationResponse):
    """Representación detallada de una conversación, incluyendo sus mensajes."""

    messages: list[MessageResponse] = Field(
        default_factory=list,
        description="Lista de mensajes ordenados cronológicamente",
    )


# ---------------------------------------------------------------------------
# Esquemas de entrada/salida – Chat en tiempo real
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Solicitud para enviar un mensaje al agente y recibir respuesta."""

    agent_id: str = Field(..., description="ID del agente que debe responder")
    message: str = Field(..., min_length=1, description="Contenido del mensaje del usuario")
    conversation_id: str | None = Field(
        default=None,
        description="ID de conversación existente; si es None se crea una nueva",
    )


class ChatResponse(BaseModel):
    """Respuesta generada por el agente en una conversación de chat."""

    reply: str = Field(..., description="Texto de respuesta generado por el agente")
    conversation_id: str = Field(..., description="ID de la conversación (nueva o existente)")
