"""
Servicio de cifrado simétrico para proteger credenciales sensibles en la DB.

Usa Fernet (AES-128-CBC con HMAC-SHA256 de la librería `cryptography`).
La clave maestra se lee de la variable de entorno ENCRYPTION_KEY.

Uso:
    from services.encryption_service import encrypt, decrypt
    cipher = encrypt("mi_token_secreto")
    plain  = decrypt(cipher)
"""

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy-loaded Fernet instance (evita import-time crash si no hay key)
# ---------------------------------------------------------------------------
_fernet = None


def _get_fernet():
    """Carga la clave Fernet una sola vez."""
    global _fernet
    if _fernet is not None:
        return _fernet

    from cryptography.fernet import Fernet
    from config import settings

    key = settings.encryption_key
    if not key:
        logger.warning(
            "ENCRYPTION_KEY no configurada. Las credenciales se almacenarán "
            "codificadas en Base64 pero SIN cifrado real (solo desarrollo)."
        )
        return None

    try:
        _fernet = Fernet(key.encode("utf-8") if isinstance(key, str) else key)
    except Exception as exc:
        logger.error("ENCRYPTION_KEY inválida: %s", exc)
        return None

    return _fernet


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def encrypt(plaintext: str) -> str:
    """
    Cifra un texto plano y retorna el ciphertext como string URL-safe Base64.

    Si no hay clave configurada (desarrollo), retorna el texto tal cual
    con un prefijo `PLAIN:` para distinguirlo del cifrado real.
    """
    if not plaintext:
        return ""

    f = _get_fernet()
    if f is None:
        # Modo desarrollo: prefijo para distinguir
        return f"PLAIN:{plaintext}"

    token = f.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt(ciphertext: str) -> str:
    """
    Descifra un ciphertext producido por `encrypt()`.

    Soporta textos almacenados sin cifrado (prefijo `PLAIN:`) para
    compatibilidad con desarrollo local.
    """
    if not ciphertext:
        return ""

    # Modo desarrollo (sin cifrado)
    if ciphertext.startswith("PLAIN:"):
        return ciphertext[6:]

    f = _get_fernet()
    if f is None:
        logger.error(
            "Se intentó descifrar un valor cifrado pero ENCRYPTION_KEY no "
            "está configurada. Retornando cadena vacía."
        )
        return ""

    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        logger.error("Error al descifrar credencial: %s", exc)
        return ""


def generate_fernet_key() -> str:
    """
    Genera una clave Fernet válida (URL-safe Base64 de 32 bytes).
    Útil para generar el valor inicial de ENCRYPTION_KEY.

    Uso en terminal:
        python -c "from services.encryption_service import generate_fernet_key; print(generate_fernet_key())"
    """
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode("utf-8")
