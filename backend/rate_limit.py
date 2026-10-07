import os
from fastapi import Request
from slowapi import Limiter

def get_real_client_ip(request: Request) -> str:
    """
    Obtiene la IP real del cliente detrás del proxy o CDN (ej. Vercel / Cloudflare).
    Evita que todos los usuarios compartan la misma IP de proxy de la lambda.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Tomar la primera IP de la cadena (la del cliente original)
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


storage_uri = os.getenv("RATE_LIMIT_STORAGE_URI", "memory://")
limiter = Limiter(
    key_func=get_real_client_ip,
    storage_uri=storage_uri,
)
