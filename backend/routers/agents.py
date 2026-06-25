"""
Router de Agentes para PLATAFORMA GENIA.

Permite listar, crear, obtener detalles, actualizar y eliminar agentes de IA.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.agent import Agent
from schemas import AgentCreate, AgentListItem, AgentResponse, AgentUpdate, AgentUsageResponse
from services.auth_service import get_current_user

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("/", response_model=list[AgentResponse])
def list_agents(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Lista todos los agentes disponibles para el usuario actual."""
    import os
    env = os.getenv("ENVIRONMENT", "development")

    if current_user["id"] != "local_dev_user":
        if env == "development":
            # En desarrollo local, asociamos automáticamente todos los agentes al usuario actual
            # para que no queden inaccesibles si el desarrollador cambia de cuenta de Google/Supabase.
            all_agents = db.query(Agent).all()
            updated = False
            for agent in all_agents:
                if agent.user_id != current_user["id"]:
                    agent.user_id = current_user["id"]
                    updated = True
            if updated:
                db.commit()
        else:
            # Si hay agentes huérfanos (user_id es None), los asociamos automáticamente al usuario actual
            orphans = db.query(Agent).filter(Agent.user_id == None).all()
            if orphans:
                for agent in orphans:
                    agent.user_id = current_user["id"]
                db.commit()

    if current_user["id"] == "local_dev_user":
        # En desarrollo local sin Supabase configurada, mostramos todos los agentes
        agents = db.query(Agent).order_by(Agent.created_at.desc()).all()
    else:
        # En producción/desarrollo con Supabase, filtramos estrictamente por el propietario creador
        agents = (
            db.query(Agent)
            .filter(Agent.user_id == current_user["id"])
            .order_by(Agent.created_at.desc())
            .all()
        )
    return agents


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Obtiene el detalle completo de un agente por su ID, validando pertenencia."""
    import os
    env = os.getenv("ENVIRONMENT", "development")

    if current_user["id"] != "local_dev_user":
        if env == "development":
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if agent and agent.user_id != current_user["id"]:
                agent.user_id = current_user["id"]
                db.commit()
        else:
            # Si el agente buscado es huérfano, lo asociamos al usuario actual antes de validar pertenencia
            orphan = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == None).first()
            if orphan:
                orphan.user_id = current_user["id"]
                db.commit()

    query = db.query(Agent).filter(Agent.id == agent_id)
    if current_user["id"] != "local_dev_user":
        query = query.filter(Agent.user_id == current_user["id"])
    
    agent = query.first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún agente con el ID {agent_id}",
        )
    return agent


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(agent_in: AgentCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Crea un nuevo agente de IA asociado al usuario actual."""
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
    """Actualiza un agente de IA existente validando pertenencia."""
    query = db.query(Agent).filter(Agent.id == agent_id)
    if current_user["id"] != "local_dev_user":
        query = query.filter(Agent.user_id == current_user["id"])

    db_agent = query.first()
    if not db_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún agente con el ID {agent_id}",
        )

    # Actualizar solo los campos que vienen en el request
    update_data = agent_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_agent, field, value)

    db.commit()
    db.refresh(db_agent)
    return db_agent


@router.delete("/{agent_id}", status_code=status.HTTP_200_OK)
def delete_agent(agent_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Elimina un agente de IA validando pertenencia."""
    query = db.query(Agent).filter(Agent.id == agent_id)
    if current_user["id"] != "local_dev_user":
        query = query.filter(Agent.user_id == current_user["id"])

    db_agent = query.first()
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
    """Obtiene el consumo de tokens y costos de un agente por modelo, validando pertenencia."""
    from models.agent_usage import AgentUsage
    
    query = db.query(Agent).filter(Agent.id == agent_id)
    if current_user["id"] != "local_dev_user":
        query = query.filter(Agent.user_id == current_user["id"])

    agent = query.first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún agente con el ID {agent_id}",
        )
    usages = db.query(AgentUsage).filter(AgentUsage.agent_id == agent_id).order_by(AgentUsage.last_used.desc()).all()
    return usages
