import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.agent import Agent
from models.conversation import Conversation
from rate_limit import limiter


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/public", tags=["Public Chat (Share)"])


class PublicChatRequest(BaseModel):
    agent_id: str = Field(..., description="ID del agente a contactar")
    message: str = Field(..., description="Mensaje del usuario")
    conversation_id: str | None = Field(default=None, description="ID de conversacion existente o null para crear nueva")


class PublicChatResponse(BaseModel):
    conversation_id: str
    reply: str


class PublicAgentInfo(BaseModel):
    id: str
    name: str


@router.post("/chat", response_model=PublicChatResponse)
@limiter.limit("30/minute")
async def public_chat(
    req: Request,
    body: PublicChatRequest,
    db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter(Agent.id == body.agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agente no encontrado",
        )

    if body.conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == body.conversation_id,
                Conversation.agent_id == body.agent_id,
            )
            .first()
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversacion no encontrada",
            )
    else:
        conversation = Conversation(
            agent_id=body.agent_id,
            channel="web",
            status="active",
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    from services.conversation_service import process_conversation_message

    reply = await process_conversation_message(
        db=db,
        agent=agent,
        conversation=conversation,
        user_message_text=body.message,
        source_channel="web",
    )

    return PublicChatResponse(conversation_id=conversation.id, reply=reply)


@router.get("/agent/{agent_id}", response_model=PublicAgentInfo)
async def public_agent_info(
    agent_id: str,
    db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agente no encontrado",
        )
    return PublicAgentInfo(id=agent.id, name=agent.name)
