"""
Modelo del Agente de IA.

Cada agente representa una configuración independiente de chatbot
con su propio prompt de sistema, proveedor de LLM, campos personalizados
y canales de comunicación habilitados.
"""

import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Integer,
    Boolean,
    DateTime,
    JSON,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship

from database import Base


class Agent(Base):
    """
    Modelo ORM para los agentes de IA de la plataforma.

    Attributes:
        id: Identificador unico (UUID hex).
        name: Nombre visible del agente.
        description: Descripcion opcional del proposito del agente.
        system_prompt: Prompt de sistema que define la personalidad y comportamiento.
        provider: Proveedor de LLM ('groq' o 'gemini').
        model: Identificador del modelo de LLM a utilizar.
        temperature: Temperatura de generacion (0.0 - 2.0).
        max_tokens: Maximo de tokens en la respuesta.
        status: Estado del agente ('active' o 'inactive').
        custom_fields: Definiciones de campos personalizados para captura de leads (JSON).
        channels: Lista de canales habilitados, ej. ['web', 'whatsapp'] (JSON).
        created_at: Fecha y hora de creacion (UTC con zona horaria).
        updated_at: Fecha y hora de ultima actualizacion (UTC con zona horaria).
    """

    __tablename__ = "agents"

    id = Column(
        String,
        primary_key=True,
        default=lambda: uuid.uuid4().hex,
        doc="Identificador unico UUID del agente",
    )
    name = Column(String(255), nullable=False, doc="Nombre del agente")
    description = Column(String(500), nullable=True, doc="Descripcion del agente")
    system_prompt = Column(
        Text,
        nullable=False,
        doc="Prompt de sistema que define el comportamiento del agente",
    )
    provider = Column(
        String(50),
        default="groq",
        nullable=False,
        doc="Proveedor de LLM: 'groq' o 'gemini'",
    )
    model = Column(
        String(100),
        default="llama-3.3-70b-versatile",
        nullable=False,
        doc="Modelo de LLM a utilizar",
    )
    temperature = Column(
        Float,
        default=0.7,
        nullable=False,
        doc="Temperatura de generacion (0.0 - 2.0)",
    )
    max_tokens = Column(
        Integer,
        default=1024,
        nullable=False,
        doc="Maximo de tokens en la respuesta",
    )
    status = Column(
        String(20),
        default="active",
        nullable=False,
        doc="Estado del agente: 'active' o 'inactive'",
    )
    custom_fields = Column(
        JSON,
        default=list,
        nullable=False,
        doc="Definiciones de campos personalizados para captura de leads",
    )
    channels = Column(
        JSON,
        default=lambda: ["web"],
        nullable=False,
        doc="Canales de comunicacion habilitados",
    )
    notification_phone = Column(
        String(50),
        nullable=True,
        doc="Número de WhatsApp del encargado para recibir notificaciones",
    )
    user_id = Column(
        String(255),
        nullable=True,
        index=True,
        doc="ID del usuario propietario en Supabase Auth",
    )
    tenant_id = Column(
        String,
        ForeignKey("tenant.id"),
        nullable=True,
        index=True,
        doc="ID del tenant propietario (multi-tenant). Nullable por compatibilidad; se promovera a NOT NULL en una fase posterior.",
    )
    enabled_mcp_tools = Column(
        JSON,
        default=list,
        nullable=True,
        doc="Lista de MCP_Tools habilitadas para el agente (por tenant)",
    )

    # --- Credenciales WhatsApp Cloud API (por agente/cliente) ---
    whatsapp_phone_number_id = Column(
        String(100),
        nullable=True,
        index=True,
        doc="Phone Number ID de Meta para este agente (único por línea de WA)",
    )
    whatsapp_access_token = Column(
        Text,
        nullable=True,
        doc="Access Token de Meta (cifrado con Fernet) para este agente",
    )
    whatsapp_app_secret = Column(
        Text,
        nullable=True,
        doc="App Secret de Meta (cifrado con Fernet) para verificación de firma HMAC",
    )
    whatsapp_verify_token = Column(
        String(255),
        nullable=True,
        doc="Token de verificación de webhook personalizado por agente",
    )
    whatsapp_connected = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Si el agente tiene WhatsApp conectado y verificado",
    )
    whatsapp_provider = Column(
        String(50),
        default="meta_cloud",
        nullable=False,
        doc="Proveedor de WhatsApp: 'meta_cloud' o 'qr_code'",
    )
    whatsapp_qr_instance_name = Column(
        String(100),
        nullable=True,
        doc="Nombre de la instancia de la API QR (Evolution API)",
    )
    whatsapp_qr_instance_token = Column(
        Text,
        nullable=True,
        doc="Token de la instancia (cifrado) para interactuar con su API",
    )
    whatsapp_qr_connected = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Si la línea QR está conectada",
    )

    # --- Google Calendar OAuth 2.0 (por agente/cliente) ---
    google_calendar_client_id = Column(
        String(255),
        nullable=True,
        doc="Client ID de Google API (OAuth 2.0) proporcionado por el cliente",
    )
    google_calendar_client_secret = Column(
        Text,
        nullable=True,
        doc="Client Secret de Google API (OAuth 2.0, cifrado con Fernet)",
    )
    google_calendar_refresh_token = Column(
        Text,
        nullable=True,
        doc="Refresh Token de Google OAuth (cifrado con Fernet) para acceso a Calendar",
    )
    google_calendar_connected = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Si el agente tiene Google Calendar conectado y autorizado",
    )
    google_calendar_email = Column(
        String(255),
        nullable=True,
        doc="Email de la cuenta de Google Calendar conectada",
    )

    # --- Transcripción de voz (STT) ---
    stt_provider = Column(
        String(50),
        default="groq_whisper",
        nullable=False,
        doc="Proveedor de transcripción de voz: groq_whisper, google_stt, deepgram, openai_whisper",
    )

    # --- Zona horaria del agente ---
    timezone = Column(
        String(50),
        default="America/Bogota",
        nullable=False,
        doc="Zona horaria del agente (ej: America/Bogota, America/Mexico_City)",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Fecha y hora de creacion",
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        doc="Fecha y hora de ultima actualizacion",
    )

    # --- Relaciones ---
    conversations = relationship(
        "Conversation",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    leads = relationship(
        "Lead",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    knowledge_documents = relationship(
        "KnowledgeDocument",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    images = relationship(
        "AgentImage",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    usages = relationship(
        "AgentUsage",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    mcp_servers = relationship(
        "MCPServerConfig",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )



    def __repr__(self) -> str:
        return f"<Agent(id={self.id!r}, name={self.name!r}, provider={self.provider!r})>"
