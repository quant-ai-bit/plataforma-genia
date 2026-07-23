"""
Esquemas Pydantic v2 para el recurso Agent.

Define los modelos de validación para crear, actualizar y serializar agentes
de IA dentro de la plataforma GENIA.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Sub-modelos auxiliares
# ---------------------------------------------------------------------------

class CustomFieldDefinition(BaseModel):
    """Definición de un campo personalizado configurable por agente."""

    key: str = Field(..., description="Clave única del campo personalizado")
    label: str = Field(..., description="Etiqueta visible para el usuario")
    type: str = Field(
        default="text",
        description="Tipo de campo: text, number, email, select, etc.",
    )
    required: bool = Field(
        default=False,
        description="Indica si el campo es obligatorio",
    )
    options: list[str] | None = Field(
        default=None,
        description="Opciones válidas (solo para tipo 'select')",
    )


# ---------------------------------------------------------------------------
# Esquemas de entrada (request bodies)
# ---------------------------------------------------------------------------

class AgentCreate(BaseModel):
    """Datos requeridos para crear un nuevo agente."""

    name: str = Field(..., min_length=1, max_length=255, description="Nombre del agente")
    description: str | None = Field(default=None, max_length=1000, description="Descripción breve del agente")
    system_prompt: str = Field(..., min_length=1, description="Prompt de sistema que define el comportamiento del agente")
    provider: str = Field(default="groq", description="Proveedor del LLM (groq, gemini, etc.)")
    model: str = Field(default="llama-3.3-70b-versatile", description="Modelo de lenguaje a utilizar")
    temperature: float = Field(default=0.7, ge=0, le=1, description="Temperatura de generación (0 = determinista, 1 = creativo)")
    max_tokens: int = Field(default=1024, ge=1, le=8192, description="Máximo de tokens en la respuesta")
    custom_fields: list[CustomFieldDefinition] = Field(
        default_factory=list,
        description="Definiciones de campos personalizados para captura de leads",
    )
    channels: list[str] = Field(
        default_factory=lambda: ["web"],
        description="Canales habilitados para el agente (web, whatsapp, telegram, etc.)",
    )
    notification_phone: str | None = Field(default=None, max_length=50, description="Teléfono de WhatsApp para notificaciones del encargado")

    # Credenciales WhatsApp Cloud API (por agente)
    whatsapp_phone_number_id: str | None = Field(default=None, max_length=100, description="Phone Number ID de la app de Meta del cliente")
    whatsapp_access_token: str | None = Field(default=None, description="Access Token permanente de la app de Meta del cliente")
    whatsapp_app_secret: str | None = Field(default=None, description="App Secret de la app de Meta del cliente")
    whatsapp_verify_token: str | None = Field(default=None, max_length=255, description="Token de verificación del webhook personalizado")
    whatsapp_provider: str = Field(default="meta_cloud", description="Proveedor de WhatsApp (meta_cloud, qr_code)")
    whatsapp_qr_instance_name: str | None = Field(default=None, max_length=100, description="Nombre de la instancia de la API QR")

    # Credenciales Google Calendar API (por agente)
    google_calendar_client_id: str | None = Field(default=None, max_length=255, description="Client ID de Google API del cliente")
    google_calendar_client_secret: str | None = Field(default=None, description="Client Secret de Google API del cliente")

    # Transcripción de voz (STT)
    stt_provider: str = Field(
        default="groq_whisper",
        description="Proveedor de transcripción de voz: groq_whisper, google_stt, deepgram, openai_whisper",
    )

    # Zona horaria
    timezone: str = Field(
        default="America/Bogota",
        description="Zona horaria del agente (ej: America/Bogota, America/Mexico_City)",
    )


class AgentUpdate(BaseModel):
    """Datos opcionales para actualizar un agente existente."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    system_prompt: str | None = Field(default=None, min_length=1)
    provider: str | None = Field(default=None)
    model: str | None = Field(default=None)
    temperature: float | None = Field(default=None, ge=0, le=1)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)
    status: str | None = Field(default=None, description="Estado del agente: active, inactive, archived")
    custom_fields: list[CustomFieldDefinition] | None = Field(default=None)
    channels: list[str] | None = Field(default=None)
    notification_phone: str | None = Field(default=None, max_length=50)

    # Credenciales WhatsApp Cloud API (por agente)
    whatsapp_phone_number_id: str | None = Field(default=None, max_length=100)
    whatsapp_access_token: str | None = Field(default=None)
    whatsapp_app_secret: str | None = Field(default=None)
    whatsapp_verify_token: str | None = Field(default=None, max_length=255)
    whatsapp_provider: str | None = Field(default=None)
    whatsapp_qr_instance_name: str | None = Field(default=None, max_length=100)

    # Credenciales Google Calendar API (por agente)
    google_calendar_client_id: str | None = Field(default=None, max_length=255)
    google_calendar_client_secret: str | None = Field(default=None)

    # Transcripción de voz (STT)
    stt_provider: str | None = Field(default=None, description="Proveedor STT")

    # Zona horaria
    timezone: str | None = Field(default=None, description="Zona horaria")


# ---------------------------------------------------------------------------
# Esquemas de salida (response bodies)
# ---------------------------------------------------------------------------

class AgentResponse(BaseModel):
    """Representación completa de un agente (detalle)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    system_prompt: str
    provider: str
    model: str
    temperature: float
    max_tokens: int
    status: str
    custom_fields: list[CustomFieldDefinition]
    channels: list[str]
    notification_phone: str | None
    whatsapp_connected: bool = False
    whatsapp_phone_number_id: str | None = None
    whatsapp_provider: str = "meta_cloud"
    whatsapp_qr_instance_name: str | None = None
    whatsapp_qr_connected: bool = False
    whatsapp_history_sync_enabled: bool = False
    whatsapp_history_synced: bool = False
    whatsapp_sync_status: str = "idle"
    google_calendar_client_id: str | None = None
    google_calendar_connected: bool = False
    google_calendar_email: str | None = None
    stt_provider: str = "groq_whisper"
    timezone: str = "America/Bogota"
    created_at: datetime
    updated_at: datetime | None

    @field_validator("whatsapp_connected", "whatsapp_qr_connected", "whatsapp_history_sync_enabled", "whatsapp_history_synced", "google_calendar_connected", mode="before")
    @classmethod
    def default_bool(cls, v):
        return v if v is not None else False

    @field_validator("whatsapp_sync_status", mode="before")
    @classmethod
    def default_sync_status(cls, v):
        return v if v is not None else "idle"

    @field_validator("whatsapp_provider", mode="before")
    @classmethod
    def default_whatsapp_provider(cls, v):
        return v if v is not None else "meta_cloud"

    @field_validator("stt_provider", mode="before")
    @classmethod
    def default_stt_provider(cls, v):
        return v if v is not None else "groq_whisper"

    @field_validator("timezone", mode="before")
    @classmethod
    def default_timezone(cls, v):
        return v if v is not None else "America/Bogota"


class AgentListItem(BaseModel):
    """Representación resumida de un agente para listados."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    provider: str
    model: str
    status: str
    channels: list[str]
    created_at: datetime
