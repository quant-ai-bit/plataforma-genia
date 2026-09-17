"""
Router de Leads para PLATAFORMA GENIA.

Permite listar, consultar y actualizar el estado CRM de los clientes potenciales (leads)
capturados por los agentes durante las conversaciones.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.lead import Lead
from models.agent import Agent
from schemas.lead import LeadResponse, LeadStatusUpdate
from services.auth_service import get_current_user
from routers.users import get_user_role_and_account

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.get("", response_model=list[LeadResponse])
def list_leads(
    agent_id: str | None = None,
    source_channel: str | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Lista todos los leads capturados.
    Si el usuario es admin, puede ver todos o filtrar por agent_id.
    Si el usuario no es admin, solo ve los leads de su agente asignado.
    """
    is_admin, user_acc = get_user_role_and_account(db, current_user)
    query = db.query(Lead).options(joinedload(Lead.agent))

    if not is_admin:
        if not user_acc or not user_acc.assigned_agent_id:
            return []
        query = query.filter(Lead.agent_id == user_acc.assigned_agent_id)
    elif agent_id:
        query = query.filter(Lead.agent_id == agent_id)

    if source_channel:
        query = query.filter(Lead.source_channel == source_channel)

    leads = query.order_by(Lead.captured_at.desc()).all()
    
    result = []
    for lead in leads:
        lead_dict = LeadResponse.model_validate(lead).model_dump()
        lead_dict["agent_name"] = lead.agent.name if lead.agent else "Agente Genia"
        if not lead_dict.get("status"):
            lead_dict["status"] = "primer_contacto"
        result.append(lead_dict)

    return result


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Obtiene el detalle completo de un lead por su ID."""
    is_admin, user_acc = get_user_role_and_account(db, current_user)
    lead = db.query(Lead).options(joinedload(Lead.agent)).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún lead con el ID {lead_id}",
        )
    if not is_admin and (not user_acc or lead.agent_id != user_acc.assigned_agent_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para acceder a este lead.",
        )
    lead_dict = LeadResponse.model_validate(lead).model_dump()
    lead_dict["agent_name"] = lead.agent.name if lead.agent else "Agente Genia"
    if not lead_dict.get("status"):
        lead_dict["status"] = "primer_contacto"
    return lead_dict


@router.patch("/{lead_id}/status", response_model=LeadResponse)
def update_lead_status(
    lead_id: str,
    status_update: LeadStatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Actualiza la etapa en el Pipeline CRM del lead."""
    is_admin, user_acc = get_user_role_and_account(db, current_user)
    lead = db.query(Lead).options(joinedload(Lead.agent)).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún lead con el ID {lead_id}",
        )
    if not is_admin and (not user_acc or lead.agent_id != user_acc.assigned_agent_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar este lead.",
        )
    
    valid_statuses = {"primer_contacto", "en_cualificacion", "cualificado", "objetivo_cumplido", "perdido"}
    if status_update.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado no válido. Debe ser uno de: {', '.join(valid_statuses)}",
        )

    lead.status = status_update.status
    db.commit()
    db.refresh(lead)

    lead_dict = LeadResponse.model_validate(lead).model_dump()
    lead_dict["agent_name"] = lead.agent.name if lead.agent else "Agente Genia"
    return lead_dict


@router.delete("/{lead_id}", status_code=status.HTTP_200_OK)
def delete_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Elimina un lead de la base de datos."""
    is_admin, user_acc = get_user_role_and_account(db, current_user)
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún lead con el ID {lead_id}",
        )
    if not is_admin and (not user_acc or lead.agent_id != user_acc.assigned_agent_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar este lead.",
        )

    db.delete(lead)
    db.commit()
    return {"status": "success", "message": f"Lead {lead_id} eliminado exitosamente."}
