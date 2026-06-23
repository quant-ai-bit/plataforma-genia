"""
Router de Conversaciones para PLATAFORMA GENIA.

Permite listar el historial de conversaciones, filtrar por agente,
obtener transcripciones detalladas de mensajes y cambiar el estado de las sesiones.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.conversation import Conversation
from schemas.conversation import ConversationDetail, ConversationResponse

router = APIRouter(prefix="/conversations", tags=["Conversations"])


class StatusUpdate(BaseModel):
    """Esquema para actualizar el estado de una conversación."""

    status: str = Field(
        ...,
        description="Nuevo estado de la conversación: active, closed o handoff",
    )


@router.get("/", response_model=list[ConversationResponse])
def list_conversations(
    agent_id: str | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Lista todas las conversaciones de la plataforma.

    Permite filtrar opcionalmente por agente y por estado.
    """
    query = db.query(Conversation)

    if agent_id:
        query = query.filter(Conversation.agent_id == agent_id)
    if status_filter:
        query = query.filter(Conversation.status == status_filter)

    conversations = query.order_by(Conversation.last_message_at.desc()).all()
    return conversations


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Obtiene una conversación detallada con todos sus mensajes asociados."""
    conversation = (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ninguna conversación con el ID {conversation_id}",
        )
    return conversation


@router.put("/{conversation_id}/status", response_model=ConversationResponse)
def update_conversation_status(
    conversation_id: str,
    status_in: StatusUpdate,
    db: Session = Depends(get_db),
):
    """Actualiza el estado de una conversación (ej. cerrar o derivar a humano)."""
    conversation = (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ninguna conversación con el ID {conversation_id}",
        )

    valid_statuses = ["active", "closed", "handoff"]
    if status_in.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Estado inválido: {status_in.status}. "
                f"Los estados permitidos son: {', '.join(valid_statuses)}"
            ),
        )

    conversation.status = status_in.status
    db.commit()
    db.refresh(conversation)
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_200_OK)
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Elimina una conversación y sus mensajes asociados."""
    conversation = (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ninguna conversación con el ID {conversation_id}",
        )

    db.delete(conversation)
    db.commit()
    return {
        "status": "success",
        "message": f"Conversación {conversation_id} eliminada exitosamente.",
    }


class SupervisorMessageIn(BaseModel):
    """Esquema para enviar un mensaje del supervisor."""
    content: str = Field(..., min_length=1, description="Contenido del mensaje")


@router.post("/{conversation_id}/send-message", status_code=status.HTTP_201_CREATED)
async def supervisor_send_message(
    conversation_id: str,
    message_in: SupervisorMessageIn,
    db: Session = Depends(get_db),
):
    """
    Envía un mensaje de toma de control (supervisor humano) al cliente.
    Si el canal es whatsapp, envía el mensaje por WhatsApp Cloud API.
    """
    conversation = (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ninguna conversación con el ID {conversation_id}",
        )

    # 1. Si es canal WhatsApp, enviar vía Meta API
    if conversation.channel == "whatsapp":
        if not conversation.contact_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La conversación es de WhatsApp pero no posee un teléfono de contacto.",
            )
        try:
            from services.whatsapp_service import send_whatsapp_text
            await send_whatsapp_text(conversation.contact_phone, message_in.content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error de Meta API al enviar mensaje: {str(e)}",
            )

    # 2. Guardar el mensaje en la BD
    from datetime import datetime, timezone
    from models.conversation import Message as DBMessage
    
    new_msg = DBMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=message_in.content,
    )
    db.add(new_msg)
    
    # Actualizar última actividad
    conversation.last_message_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(new_msg)
    
    return {
        "status": "success",
        "message": {
            "id": new_msg.id,
            "role": new_msg.role,
            "content": new_msg.content,
            "sent_at": new_msg.sent_at,
        }
    }
