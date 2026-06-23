"""
Capa de proveedores de modelo (Model Providers) para PLATAFORMA GENIA.

Expone la interfaz comun `ModelProvider`, los DTO de generacion y los
proveedores concretos (Vertex AI / Gemini, Groq, OpenRouter).
"""

from services.providers.base import (  # noqa: F401
    GenerationRequest,
    GenerationResult,
    ModelProvider,
    ProviderError,
    ProviderTimeout,
    ModelUnavailableError,
)
