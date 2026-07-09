"""Modelo de base de datos para almacenar el estado de agotamiento y cuota diaria de los modelos gratuitos."""

from sqlalchemy import Column, String, Boolean, DateTime, Integer, func
from database import Base


class FreeModelStatus(Base):
    """Estado y métricas de cuota de cada modelo gratuito."""

    __tablename__ = "free_model_statuses"

    id = Column(
        String,
        primary_key=True,
        doc="Identificador único formateado como provider:model (ej: groq:llama-3.3-70b-versatile)",
    )
    provider = Column(String(50), nullable=False, doc="Proveedor del modelo (groq, gemini, openrouter)")
    model = Column(String(100), nullable=False, doc="Identificador del modelo")
    is_exhausted = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Si el modelo está agotado (límite superado)",
    )
    exhausted_until = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Marca de tiempo hasta la cual el modelo está en cooldown/bloqueado",
    )
    exhausted_reason = Column(
        String(255),
        nullable=True,
        doc="Motivo de la inhabilitación (ej: Rate limit 429, OpenRouter 402)",
    )
    tokens_used_today = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Cantidad de tokens consumidos en el día actual",
    )
    requests_used_today = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Cantidad de peticiones enviadas en el día actual",
    )
    last_used = Column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
        doc="Última vez que se usó este modelo para generar respuesta",
    )

    def __repr__(self) -> str:
        return f"<FreeModelStatus(id={self.id!r}, is_exhausted={self.is_exhausted!r}, exhausted_until={self.exhausted_until!r})>"
