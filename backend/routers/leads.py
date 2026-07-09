"""
Router de Leads para PLATAFORMA GENIA.

Permite listar y consultar los datos de los clientes potenciales (leads)
capturados por los agentes durante las conversaciones.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.lead import Lead
from schemas.lead import LeadResponse

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
    query = db.query(Lead)

    if agent_id:
        query = query.filter(Lead.agent_id == agent_id)
    if source_channel:
        query = query.filter(Lead.source_channel == source_channel)

    leads = query.order_by(Lead.captured_at.desc()).all()
    return leads


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    """Obtiene el detalle completo de un lead por su ID."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún lead con el ID {lead_id}",
        )
    return lead


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
