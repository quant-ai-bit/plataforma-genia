"""
Módulo de Seguridad y Control de Acceso Centralizado para PLATAFORMA GENIA.

Provee dependencias seguras para:
- Autenticación de cron jobs externos (Vercel Cron / GitHub Actions).
- Verificación de webhooks de WAHA mediante API key compartida.
- Verificación de rol Administrador (respaldado por Base de Datos).
- Verificación de propiedad y aislamiento Multi-Tenant por agente (require_agent_access).
"""

import hmac
import logging
from typing import Optional
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.agent import Agent
from models.user_account import UserAccount
from services.auth_service import get_current_user

logger = logging.getLogger(__name__)


# ── 1. Verificación de Cron Secret ──────────────────────────────────────────

def verify_cron_secret(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    cron_secret_header: Optional[str] = Header(None, alias="X-Cron-Secret"),
) -> bool:
    """
    Verifica que la petición de cron incluya el secreto configurado en CRON_SECRET.
    
    Acepta:
      - Authorization: Bearer <CRON_SECRET> (estándar de Vercel Cron)
      - X-Cron-Secret: <CRON_SECRET> (útil para GitHub Actions o curls manuales)
    """
    expected_secret = getattr(settings, "cron_secret", "").strip()
    if not expected_secret:
        if settings.is_production:
            logger.error("[CRON_SECURITY] CRON_SECRET no está configurado en producción. Rechazando petición.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Cron endpoint no configurado con seguridad.",
            )
        # En desarrollo local sin secreto configurado permitimos pasar con advertencia
        logger.warning("[CRON_SECURITY] CRON_SECRET no configurado (modo desarrollo local).")
        return True

    token = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()
        elif len(parts) == 1:
            token = parts[0].strip()
    elif cron_secret_header:
        token = cron_secret_header.strip()

    if not token or not hmac.compare_digest(token, expected_secret):
        logger.warning("[CRON_SECURITY] Intento de acceso a endpoint cron con secreto inválido o faltante.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado para ejecutar tareas programadas (Cron Secret inválido).",
        )

    return True


# ── 2. Verificación de Webhooks WAHA ────────────────────────────────────────

def verify_waha_webhook(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-Api-Key"),
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
) -> bool:
    """
    Verifica que el webhook de WAHA provenga de una fuente autorizada.
    
    WAHA y el Audio Proxy (VPS) envían 'X-Api-Key: <WAHA_API_KEY>'.
    Soporta despliegue seguro con WAHA_WEBHOOK_AUTH_MODE:
      - 'log': Registra si falta o es inválida sin bloquear (fase de prueba cero downtime).
      - 'enforce': Rechaza con 401 si no coincide exactamente.
    """
    mode = getattr(settings, "waha_webhook_auth_mode", "log").lower().strip()
    expected_key = (getattr(settings, "waha_api_key", "") or "").strip()

    provided_key = (x_api_key or x_webhook_secret or "").strip()
    
    # También chequear query param como fallback si WAHA no inyecta headers
    if not provided_key:
        provided_key = request.query_params.get("secret", "").strip()

    is_valid = bool(expected_key and provided_key and hmac.compare_digest(provided_key, expected_key))

    if not is_valid:
        msg = f"[WAHA_SECURITY] Webhook recibido sin clave válida desde {request.client.host if request.client else 'desconocido'}"
        if mode == "enforce":
            logger.error(f"{msg} - Bloqueado (401)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Clave de autenticación de webhook inválida o ausente.",
            )
        else:
            logger.warning(f"{msg} - Permitido por modo 'log' (cero downtime)")
            return False

    return True


# ── 3. Roles y Aislamiento de Usuario (DB First) ───────────────────────────

def get_user_role_and_account(
    db: Session,
    current_user: dict
) -> tuple[bool, Optional[UserAccount]]:
    """
    Determina si el usuario es administrador y retorna su cuenta.
    
    Seguridad:
    - La fuente primaria de verdad es la base de datos (user_accounts.role == 'admin').
    - El listado ADMIN_EMAILS sirve solo para bootstrapping si el email viene verificado.
    - Evita suplantación validando principalmente por user_id.
    """
    user_id = current_user.get("id")
    email = (current_user.get("email") or "").strip().lower()

    if not user_id:
        return False, None

    # En entorno puramente local
    if user_id == "local_dev_user" and not settings.is_production:
        return True, None

    user_acc = db.query(UserAccount).filter(UserAccount.id == user_id).first()
    if not user_acc and email:
        # Fallback de búsqueda si el ID aún no está sincronizado
        user_acc = db.query(UserAccount).filter(UserAccount.email == email).first()
        if user_acc:
            user_acc.id = user_id
            db.commit()

    # Verificar si es admin por BD
    if user_acc and user_acc.role == "admin" and user_acc.status == "active":
        return True, user_acc

    # Bootstrap por variable de entorno ADMIN_EMAILS
    env_admins = {e.strip().lower() for e in getattr(settings, "admin_emails", "").split(",") if e.strip()}
    if email and email in env_admins:
        if user_acc:
            if user_acc.role != "admin" or user_acc.status != "active":
                user_acc.role = "admin"
                user_acc.status = "active"
                db.commit()
                db.refresh(user_acc)
            return True, user_acc
        else:
            # Crear cuenta admin bootstrapped
            new_admin = UserAccount(
                id=user_id,
                email=email,
                role="admin",
                status="active",
                assigned_agent_id=None,
            )
            db.add(new_admin)
            db.commit()
            db.refresh(new_admin)
            return True, new_admin

    return False, user_acc


def require_admin(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> UserAccount:
    """Dependencia que restringe endpoints exclusivamente a administradores verificados."""
    is_admin, user_acc = get_user_role_and_account(db, current_user)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido: Se requieren permisos de Administrador.",
        )
    return user_acc


def require_agent_access(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> Agent:
    """
    Dependencia de aislamiento multi-tenant reutilizable.
    
    Verifica que:
    1. El agente exista.
    2. Si el usuario es administrador, conceder acceso completo.
    3. Si es un usuario cliente regular:
       - Debe tener su cuenta 'active'.
       - Su `assigned_agent_id` debe coincidir exactamente con el `agent_id` solicitado.
       De lo contrario, retorna 403 Forbidden para evitar fuga de datos entre clientes.
    """
    is_admin, user_acc = get_user_role_and_account(db, current_user)

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún agente con el ID {agent_id}",
        )

    if is_admin:
        return agent

    if not user_acc or user_acc.status != "active" or user_acc.assigned_agent_id != agent_id:
        logger.warning(
            "[AUTHZ] Acceso denegado al agente %s para el usuario %s (asignado: %s, status: %s)",
            agent_id,
            current_user.get("email"),
            user_acc.assigned_agent_id if user_acc else "ninguno",
            user_acc.status if user_acc else "sin_cuenta",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes autorización para acceder o modificar los recursos de este agente.",
        )

    return agent
