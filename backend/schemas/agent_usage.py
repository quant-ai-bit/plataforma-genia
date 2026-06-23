"""Esquemas Pydantic v2 para el recurso AgentUsage."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AgentUsageResponse(BaseModel):
    """Representación del consumo de tokens y costo por agente y modelo."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    model: str
    prompt_tokens: int = Field(..., description="Cantidad de tokens de entrada (prompt)")
    completion_tokens: int = Field(..., description="Cantidad de tokens de salida (completion)")
    total_tokens: int = Field(..., description="Suma de tokens de entrada y salida")
    cost: float = Field(..., description="Costo total acumulado en USD")
    last_used: datetime
