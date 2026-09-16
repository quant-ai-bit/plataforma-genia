"""
Router de Agentes para PLATAFORMA GENIA.

Permite listar, crear, obtener detalles, actualizar y eliminar agentes de IA.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from typing import Optional
from database import get_db
from models.agent import Agent
from models.user_account import UserAccount
from schemas import AgentCreate, AgentListItem, AgentResponse, AgentUpdate, AgentUsageResponse
from services.auth_service import get_current_user
from routers.users import get_admin_emails

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["Agents"])


def get_user_role_and_account(db: Session, current_user: dict) -> tuple[bool, Optional[UserAccount]]:
    """Determina si el usuario es administrador y retorna su cuenta si existe."""
    user_id = current_user.get("id")
    email = (current_user.get("email") or "").strip().lower()
    admins = get_admin_emails()

    if email in admins or user_id == "local_dev_user":
        return True, None

    user_acc = db.query(UserAccount).filter(
        (UserAccount.id == user_id) | (UserAccount.email == email)
    ).first()

    if user_acc and user_acc.role == "admin":
        return True, user_acc

    return False, user_acc


@router.get("", response_model=list[AgentResponse])
def list_agents(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Lista los agentes disponibles según los permisos del usuario."""
    try:
        is_admin, user_acc = get_user_role_and_account(db, current_user)

        if is_admin:
            agents = db.query(Agent).order_by(Agent.created_at.desc()).all()
        else:
            if not user_acc or user_acc.status != "active" or not user_acc.assigned_agent_id:
                # Si el usuario no está activo o no tiene agente asignado, lista vacía
                return []
            agents = db.query(Agent).filter(Agent.id == user_acc.assigned_agent_id).all()

        logger.info("[AGENTS] list_agents called by user=%s (is_admin=%s), found %d agents", current_user.get("id"), is_admin, len(agents))

        result = []
        for agent in agents:
            try:
                serialized = AgentResponse.model_validate(agent)
                result.append(serialized)
            except Exception as e:
                logger.warning("[AGENTS] Skipping agent %s (%s) due to serialization error: %s", agent.id, agent.name, str(e))
                continue

        return result
    except Exception as e:
        logger.error("[AGENTS] Fatal error in list_agents: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar agentes.",
        )


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Obtiene el detalle completo de un agente por su ID, validando permisos."""
    is_admin, user_acc = get_user_role_and_account(db, current_user)

    if not is_admin:
        if not user_acc or user_acc.status != "active" or user_acc.assigned_agent_id != agent_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes autorización para acceder a este agente. Tu cuenta debe ser verificada y asignada por un administrador.",
            )

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún agente con el ID {agent_id}",
        )
    return agent


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(agent_in: AgentCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Crea un nuevo agente de IA (solo administradores)."""
    is_admin, _ = get_user_role_and_account(db, current_user)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden crear nuevos agentes.",
        )

    from services.encryption_service import encrypt

    # Convertir las definiciones de custom_fields a diccionarios para almacenamiento JSON
    custom_fields_dict = [cf.model_dump() for cf in agent_in.custom_fields]

    db_agent = Agent(
        name=agent_in.name,
        description=agent_in.description,
        system_prompt=agent_in.system_prompt,
        provider=agent_in.provider,
        model=agent_in.model,
        temperature=agent_in.temperature,
        max_tokens=agent_in.max_tokens,
        custom_fields=custom_fields_dict,
        channels=agent_in.channels,
        notification_phone=agent_in.notification_phone,
        google_calendar_client_id=agent_in.google_calendar_client_id,
        google_calendar_client_secret=encrypt(agent_in.google_calendar_client_secret) if agent_in.google_calendar_client_secret else None,
        stt_provider=agent_in.stt_provider or "groq_whisper",
        timezone=agent_in.timezone or "America/Bogota",
        user_id=current_user["id"] if current_user["id"] != "local_dev_user" else None
    )

    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent


@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: str,
    agent_in: AgentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Actualiza un agente de IA existente (solo administradores)."""
    is_admin, _ = get_user_role_and_account(db, current_user)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden modificar agentes.",
        )

    from services.encryption_service import encrypt

    db_agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not db_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún agente con el ID {agent_id}",
        )

    # Actualizar solo los campos que vienen en el request
    update_data = agent_in.model_dump(exclude_unset=True)

    if "google_calendar_client_secret" in update_data and update_data["google_calendar_client_secret"]:
        update_data["google_calendar_client_secret"] = encrypt(update_data["google_calendar_client_secret"])

    for field, value in update_data.items():
        setattr(db_agent, field, value)

    db.commit()
    db.refresh(db_agent)
    return db_agent


@router.delete("/{agent_id}", status_code=status.HTTP_200_OK)
def delete_agent(agent_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Elimina un agente de IA (solo administradores)."""
    is_admin, _ = get_user_role_and_account(db, current_user)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden eliminar agentes.",
        )

    db_agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not db_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún agente con el ID {agent_id}",
        )

    db.delete(db_agent)
    db.commit()
    return {"status": "success", "message": f"Agente {agent_id} eliminado exitosamente."}


@router.get("/{agent_id}/usage", response_model=list[AgentUsageResponse])
def get_agent_usage(agent_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Obtiene el consumo de tokens y costos de un agente por modelo, validando permisos."""
    from models.agent_usage import AgentUsage
    
    is_admin, user_acc = get_user_role_and_account(db, current_user)
    if not is_admin:
        if not user_acc or user_acc.status != "active" or user_acc.assigned_agent_id != agent_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes autorización para ver el consumo de este agente.",
            )

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún agente con el ID {agent_id}",
        )
    usages = db.query(AgentUsage).filter(AgentUsage.agent_id == agent_id).order_by(AgentUsage.last_used.desc()).all()
    return usages
