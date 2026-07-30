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

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.get("", response_model=list[LeadResponse])
def list_leads(
    agent_id: str | None = None,
    source_channel: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Lista todos los leads capturados.
    Permite filtrar opcionalmente por agente y por canal de origen.
    """
    query = db.query(Lead).options(joinedload(Lead.agent))

    if agent_id:
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
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    """Obtiene el detalle completo de un lead por su ID."""
    lead = db.query(Lead).options(joinedload(Lead.agent)).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún lead con el ID {lead_id}",
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
):
    """Actualiza la etapa en el Pipeline CRM del lead."""
    lead = db.query(Lead).options(joinedload(Lead.agent)).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún lead con el ID {lead_id}",
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
def delete_lead(lead_id: str, db: Session = Depends(get_db)):
    """Elimina un lead de la base de datos."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún lead con el ID {lead_id}",
        )

    db.delete(lead)
    db.commit()
    return {"status": "success", "message": f"Lead {lead_id} eliminado exitosamente."}
