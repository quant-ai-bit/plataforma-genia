"""
Router de Gestión de Usuarios y Control de Acceso para PLATAFORMA GENIA.

Permite:
- Consultar el perfil propio y auto-registrar usuarios nuevos en estado 'pending'.
- Notificar por correo a los administradores cuando un usuario se registra.
- Listar usuarios pendientes y autorizarlos asignándoles un agente de IA.
- Controlar roles de acceso (admin / user).
"""

import os
import logging
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models.user_account import UserAccount
from models.agent import Agent
from services.auth_service import get_current_user
from services.email_service import notify_admin_new_user_registered, notify_user_account_approved

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

# Correos administrativos autorizados por defecto
DEFAULT_ADMIN_EMAILS = {
    "alejandr.ia.8725@gmail.com",
    "conecta@genia.com.co",
    "alejandro_baena@hotmail.com",
    "baenalejandro@gmail.com",
}

def get_admin_emails() -> set[str]:
    """Obtiene el conjunto de correos con permisos de administrador."""
    admins = set(DEFAULT_ADMIN_EMAILS)
    env_admins = os.getenv("ADMIN_EMAILS", "")
    if env_admins:
        for em in env_admins.split(","):
            cleaned = em.strip().lower()
            if cleaned:
                admins.add(cleaned)
    return admins


# --- Esquemas Pydantic ---

class AssignedAgentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


class UserAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    role: str
    status: str
    assigned_agent_id: Optional[str] = None
    assigned_agent: Optional[AssignedAgentSummary] = None
    created_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None


class UserAuthorizeRequest(BaseModel):
    assigned_agent_id: str


class PendingUsersCountResponse(BaseModel):
    count: int
    users: List[UserAccountResponse]


# --- Dependencia para verificar rol Admin ---

def require_admin(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> UserAccount:
    """Verifica que el usuario solicitante tenga rol de administrador."""
    user_id = current_user.get("id")
    email = (current_user.get("email") or "").strip().lower()
    admin_emails = get_admin_emails()

    # Buscar usuario en la base de datos
    user_acc = db.query(UserAccount).filter(
        (UserAccount.id == user_id) | (UserAccount.email == email)
    ).first()

    is_admin = False
    if email in admin_emails:
        is_admin = True
    elif user_acc and user_acc.role == "admin":
        is_admin = True

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido: Se requieren permisos de Administrador.",
        )

    return user_acc


def get_user_role_and_account(db: Session, current_user: dict) -> tuple[bool, Optional[UserAccount]]:
    """Determina si el usuario es administrador y retorna su cuenta si existe."""
    user_id = current_user.get("id")
    email = (current_user.get("email") or "").strip().lower()
    admin_emails = get_admin_emails()

    user_acc = db.query(UserAccount).filter(
        (UserAccount.id == user_id) | (UserAccount.email == email)
    ).first()

    if email in admin_emails or user_id == "local_dev_user":
        return True, user_acc

    if user_acc and user_acc.role == "admin":
        return True, user_acc

    return False, user_acc


# --- Endpoints ---

@router.get("/me", response_model=UserAccountResponse)
def get_or_create_me(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Obtiene el perfil del usuario autenticado.
    Si es la primera vez que ingresa, se crea su registro en la base de datos.
    - Si su correo está en la lista de administradores -> rol='admin', status='active'.
    - Si es un nuevo cliente -> rol='user', status='pending' y notifica a los administradores por email.
    """
    user_id = current_user.get("id")
    email = (current_user.get("email") or "").strip().lower()

    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo obtener la identidad del usuario desde el token.",
        )

    admin_emails = get_admin_emails()

    # Buscar si ya existe por ID o email
    user_acc = db.query(UserAccount).filter(
        (UserAccount.id == user_id) | (UserAccount.email == email)
    ).first()

    if not user_acc:
        # Nuevo registro
        is_admin = email in admin_emails
        role = "admin" if is_admin else "user"
        initial_status = "active" if is_admin else "pending"

        user_acc = UserAccount(
            id=user_id,
            email=email,
            role=role,
            status=initial_status,
            assigned_agent_id=None,
        )
        db.add(user_acc)
        db.commit()
        db.refresh(user_acc)

        logger.info("[USERS] Nuevo usuario creado: %s (role=%s, status=%s)", email, role, initial_status)

        # Si es usuario regular pendiente, enviar notificación por correo al admin
        if initial_status == "pending":
            notify_admin_new_user_registered(user_email=email, user_id=user_id)
    else:
        # Si ya existe, verificar si debe promoverse a admin
        if email in admin_emails and (user_acc.role != "admin" or user_acc.status != "active"):
            user_acc.role = "admin"
            user_acc.status = "active"
            db.commit()
            db.refresh(user_acc)

        # Actualizar ID si cambió
        if user_acc.id != user_id:
            user_acc.id = user_id
            db.commit()
            db.refresh(user_acc)

    return user_acc


@router.get("/pending", response_model=PendingUsersCountResponse)
def list_pending_users(
    db: Session = Depends(get_db),
    _admin: UserAccount = Depends(require_admin),
):
    """
    (Solo Administradores)
    Obtiene la lista de usuarios en estado 'pending' y el contador total.
    Utilizado por la campana de notificaciones de la interfaz.
    """
    pending = (
        db.query(UserAccount)
        .filter(UserAccount.status == "pending")
        .order_by(UserAccount.created_at.desc())
        .all()
    )
    return {
        "count": len(pending),
        "users": pending,
    }


@router.get("", response_model=List[UserAccountResponse])
def list_all_users(
    db: Session = Depends(get_db),
    _admin: UserAccount = Depends(require_admin),
):
    """
    (Solo Administradores)
    Lista todos los usuarios registrados en el sistema, ordenados por fecha de creación.
    """
    return db.query(UserAccount).order_by(UserAccount.created_at.desc()).all()


@router.post("/{user_id}/authorize", response_model=UserAccountResponse)
def authorize_user(
    user_id: str,
    payload: UserAuthorizeRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _admin: UserAccount = Depends(require_admin),
):
    """
    (Solo Administradores)
    Aprueba a un usuario pendiente y le asigna el agente de IA seleccionado.
    """
    target_user = db.query(UserAccount).filter(UserAccount.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {user_id} no encontrado.",
        )

    # Validar que el agente exista
    agent = db.query(Agent).filter(Agent.id == payload.assigned_agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agente con ID {payload.assigned_agent_id} no existe.",
        )

    target_user.status = "active"
    target_user.assigned_agent_id = agent.id
    target_user.approved_at = func.now()
    target_user.approved_by = current_user.get("email") or "admin"

    db.commit()
    db.refresh(target_user)

    logger.info(
        "[USERS] Usuario %s autorizado con agente %s por %s",
        target_user.email,
        agent.name,
        target_user.approved_by,
    )

    # Notificar al usuario por correo electrónico que su cuenta fue conectada
    try:
        notify_user_account_approved(user_email=target_user.email, agent_name=agent.name)
    except Exception as e:
        logger.error("[USERS] Error al enviar notificación al usuario %s: %s", target_user.email, str(e))

    return target_user


@router.post("/{user_id}/reject", response_model=UserAccountResponse)
def reject_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _admin: UserAccount = Depends(require_admin),
):
    """
    (Solo Administradores)
    Rechaza o suspende la cuenta de un usuario.
    """
    target_user = db.query(UserAccount).filter(UserAccount.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {user_id} no encontrado.",
        )

    target_user.status = "rejected"
    db.commit()
    db.refresh(target_user)

    logger.info("[USERS] Usuario %s rechazado por %s", target_user.email, current_user.get("email"))
    return target_user
