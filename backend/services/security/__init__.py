"""
Paquete de dependencias de seguridad para la API publica multi-tenant.

Expone las dependencias FastAPI `require_tenant` (autenticacion por API key +
resolucion de tenant) y `enforce_subscription` (enforcement de suscripcion y
limite de uso).

Feature: genia-agent-platform (Tarea 3.3)
"""

from services.security.api_key_dep import (  # noqa: F401
    enforce_subscription,
    require_tenant,
)