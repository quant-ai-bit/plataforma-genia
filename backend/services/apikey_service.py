"""
apikey_service: emision, hashing, consulta y revocacion de API keys.

Por seguridad solo se persiste el hash (SHA-256 + pepper) de cada API key; el
secreto en claro se devuelve una unica vez al generarlo y nunca se almacena.
El pepper se lee desde `settings.api_key_pepper` (variable de entorno
`API_KEY_PEPPER`), nunca hardcodeado.

Feature: genia-agent-platform (Tarea 3.2)
"""

import hashlib
import logging
import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from config import settings
from models.api_key import ApiKey

logger = logging.getLogger(__name__)

# Prefijo legible para identificar visualmente las keys de la plataforma.
KEY_PREFIX = "genia_sk_"
# Longitud (bytes) del secreto aleatorio antes de codificar en URL-safe base64.
SECRET_NBYTES = 32
# Numero de caracteres del secreto que se guardan como `prefix` (identificacion).
PREFIX_VISIBLE_CHARS = 12


def hash_api_key(raw: str) -> str:
    """
    Calcula el hash SHA-256 (con pepper) de una API key en claro.

    El pepper se concatena al secreto antes de hashear, de modo que un volcado
    de la base de datos no permita verificar keys sin conocer el pepper.

    Args:
        raw: API key en texto plano.

    Returns:
        Digest hexadecimal SHA-256 de `raw + pepper`.
    """
    pepper = settings.api_key_pepper or ""
    digest = hashlib.sha256(f"{raw}{pepper}".encode("utf-8")).hexdigest()
    return digest


def generate(db: Session, tenant_id: str) -> tuple[str, ApiKey]:
    """
    Genera una nueva API key para un tenant.

    Crea un secreto aleatorio criptograficamente seguro, persiste unicamente su
    hash (SHA-256 + pepper) junto a un `prefix` visible, y devuelve el secreto en
    claro UNA sola vez para que el llamador lo entregue al tenant.

    Args:
        db: Sesion de base de datos.
        tenant_id: Identificador del tenant propietario de la key.

    Returns:
        Tupla `(secreto_en_claro, api_key)` donde `api_key` es la fila persistida
        (solo con el hash y el prefijo, nunca el secreto en claro).
    """
    raw_secret = f"{KEY_PREFIX}{secrets.token_urlsafe(SECRET_NBYTES)}"
    key_hash = hash_api_key(raw_secret)
    prefix = raw_secret[:PREFIX_VISIBLE_CHARS]

    api_key = ApiKey(
        tenant_id=tenant_id,
        key_hash=key_hash,
        prefix=prefix,
    )
    db.add(api_key)
    db.flush()
    logger.info("API key emitida para tenant %s (prefix=%s)", tenant_id, prefix)
    return raw_secret, api_key


def get_active_by_hash(db: Session, key_hash: str) -> ApiKey | None:
    """
    Recupera una API key activa (no revocada) por su hash.

    Args:
        db: Sesion de base de datos.
        key_hash: Hash SHA-256 + pepper de la key buscada.

    Returns:
        La `ApiKey` activa correspondiente o `None` si no existe o esta revocada.
    """
    if not key_hash:
        return None
    return (
        db.query(ApiKey)
        .filter(ApiKey.key_hash == key_hash, ApiKey.revoked_at.is_(None))
        .first()
    )


def revoke(db: Session, api_key_id: str) -> ApiKey | None:
    """
    Revoca una API key estableciendo su marca de tiempo de revocacion.

    Args:
        db: Sesion de base de datos.
        api_key_id: Identificador de la API key a revocar.

    Returns:
        La `ApiKey` revocada, o `None` si no existe.
    """
    api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
    if api_key is None:
        return None
    if api_key.revoked_at is None:
        api_key.revoked_at = datetime.now(timezone.utc)
        db.flush()
        logger.info("API key %s revocada", api_key_id)
    return api_key

def get_active_for_tenant(db: Session, tenant_id: str) -> ApiKey | None:
    """
    Recupera la API key activa (no revocada) mas reciente de un tenant.

    Args:
        db: Sesion de base de datos.
        tenant_id: Identificador del tenant.

    Returns:
        La `ApiKey` activa del tenant o `None` si no tiene ninguna.
    """
    if not tenant_id:
        return None
    return (
        db.query(ApiKey)
        .filter(ApiKey.tenant_id == tenant_id, ApiKey.revoked_at.is_(None))
        .order_by(ApiKey.created_at.desc())
        .first()
    )


def issue(
    db: Session, tenant_id: str, rotate: bool = False
) -> tuple[str | None, ApiKey]:
    """
    Emite (idempotente) una API key para el tenant durante el aprovisionamiento.

    Si el tenant ya tiene una API key activa y `rotate` es False, NO re-emite el
    secreto: devuelve `(None, api_key_existente)` para no exponer un nuevo
    secreto en re-ejecuciones. Si no tiene ninguna o `rotate=True`, genera una
    nueva (revocando la anterior cuando se rota) y devuelve el secreto en claro
    una unica vez.

    Args:
        db: Sesion de base de datos.
        tenant_id: Identificador del tenant.
        rotate: Si True, fuerza la rotacion emitiendo una key nueva.

    Returns:
        Tupla `(secreto_en_claro_o_None, api_key)`.
    """
    existing = get_active_for_tenant(db, tenant_id)
    if existing is not None and not rotate:
        return None, existing
    if existing is not None and rotate:
        revoke(db, existing.id)
    return generate(db, tenant_id)
