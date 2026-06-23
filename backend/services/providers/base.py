"""
Interfaz comun de proveedores de modelo y DTO de generacion.

Define el contrato `ModelProvider` que implementan los proveedores concretos
(Vertex AI / Gemini, Groq, OpenRouter), los objetos de peticion/resultado y las
excepciones de dominio usadas por el `Model_Service` para la orquestacion de
seleccion, timeout, retry y fallback.

Feature: genia-agent-platform (Tarea 2.1)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class GenerationRequest:
    """
    Peticion de generacion enviada a un proveedor de modelo.

    Attributes:
        messages: Historial de mensajes en formato chat ([{"role", "content"}]).
        system_prompt: Prompt de sistema opcional.
        tools: Esquemas de MCP_Tool disponibles (function-calling), opcional.
        max_tokens: Maximo de tokens en la respuesta.
        temperature: Temperatura de generacion.
    """

    messages: list[dict]
    system_prompt: str | None = None
    tools: list[dict] | None = None
    max_tokens: int = 1024
    temperature: float = 0.7


@dataclass
class GenerationResult:
    """
    Resultado de una generacion devuelto por un proveedor de modelo.

    Attributes:
        text: Texto generado por el modelo.
        tool_calls: Llamadas a herramientas solicitadas por el modelo.
        provider_name: Nombre del proveedor que produjo el resultado.
        model: Identificador del modelo utilizado.
        input_tokens: Tokens de entrada consumidos.
        output_tokens: Tokens de salida generados.
    """

    text: str
    provider_name: str
    model: str
    tool_calls: list[dict] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0


class ModelProvider(ABC):
    """
    Interfaz comun de un proveedor de modelo.

    Cada proveedor concreto expone un `name` identificador y un metodo
    asincrono `generate` que produce un `GenerationResult` o lanza una de las
    excepciones de dominio (`ProviderTimeout`, `ProviderError`).
    """

    name: str = "base"

    @abstractmethod
    async def generate(
        self, req: GenerationRequest, timeout_s: float
    ) -> GenerationResult:
        """Genera una respuesta a partir de `req` respetando `timeout_s` segundos."""
        raise NotImplementedError


class ProviderError(Exception):
    """Error generico al invocar un proveedor de modelo."""


class ProviderTimeout(ProviderError):
    """El proveedor de modelo no respondio dentro del timeout configurado."""


class ModelUnavailableError(Exception):
    """Todos los proveedores de modelo fallaron; el servicio no esta disponible (HTTP 503)."""

    def __init__(self, detail: str = "Model service unavailable"):
        self.detail = detail
        super().__init__(detail)
