"""
Excepciones de dominio centralizadas de PLATAFORMA GENIA (genia-agent-platform).

Estas excepciones representan condiciones de error de negocio que los
manejadores centralizados de FastAPI (registrados en `main.py`) mapean a
codigos HTTP, sin exponer secretos ni detalles internos:

- AuthError              -> 401 (autenticacion/API key invalida)
- CrossTenantError       -> 403 (acceso a recurso de otro tenant)
- SubscriptionInactiveError -> 402 (suscripcion inactiva/impaga/cancelada)
- UsageLimitError        -> 429 (limite de uso del plan excedido)

`ModelUnavailableError` (definida en `services.providers.base`) se mapea a 503.

Feature: genia-agent-platform (Tarea 11.2)
"""


class DomainError(Exception):
    """Error de dominio base con un mensaje publico seguro (sin secretos)."""

    #: Codigo HTTP por defecto asociado a la excepcion.
    status_code: int = 400
    #: Mensaje publico por defecto (no debe contener secretos ni stack traces).
    public_message: str = "Solicitud invalida"

    def __init__(self, message: str | None = None):
        self.public_message = message or self.public_message
        super().__init__(self.public_message)


class AuthError(DomainError):
    """Autenticacion fallida o API key invalida/revocada (HTTP 401)."""

    status_code = 401
    public_message = "Autenticacion requerida o invalida"


class CrossTenantError(DomainError):
    """Intento de acceso a un recurso perteneciente a otro tenant (HTTP 403)."""

    status_code = 403
    public_message = "Acceso no autorizado al recurso del tenant"


class SubscriptionInactiveError(DomainError):
    """La suscripcion del tenant no esta activa (HTTP 402)."""

    status_code = 402
    public_message = "Suscripcion inactiva"


class UsageLimitError(DomainError):
    """El tenant supero el limite de uso de su plan (HTTP 429)."""

    status_code = 429
    public_message = "Limite de uso excedido"
