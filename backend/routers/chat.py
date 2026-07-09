"""
Router de Chat para PLATAFORMA GENIA.

Gestiona las conversaciones en tiempo real con los agentes, el almacenamiento
de historial de mensajes y la activación de la captura de leads.
"""

from datetime import datetime, timezone, timedelta
import logging

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from database import get_db
from models.agent import Agent
from models.agent_image import AgentImage
from models.conversation import Conversation, Message
from schemas.conversation import ChatRequest, ChatResponse
from services.ai_service import chat_with_agent
from services.knowledge_service import retrieve_context
from services.lead_service import extract_and_save_lead


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat Sandbox"])


@router.post("", response_model=ChatResponse)
async def chat_sandbox(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Envía un mensaje a un agente y recibe su respuesta.

    Si no se envía un `conversation_id`, se inicia una nueva conversación.
    """
    # 1. Verificar si el agente existe
    agent = db.query(Agent).filter(Agent.id == request.agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún agente con el ID {request.agent_id}",
        )

    # 2. Obtener o crear la conversación
    conversation = None
    if request.conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == request.conversation_id,
                Conversation.agent_id == request.agent_id,
            )
            .first()
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"No se encontró la conversación con ID {request.conversation_id} "
                    f"asociada al agente {request.agent_id}"
                ),
            )
    else:
        # Crear nueva conversación
        conversation = Conversation(
            agent_id=request.agent_id,
            channel="web",
            status="active",
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        logger.info(
            "Nueva conversación creada para el agente %s (ID: %s)",
            request.agent_id,
            conversation.id,
        )

    # 3. Procesar el mensaje a través del servicio unificado de conversación
    from services.conversation_service import process_conversation_message

    reply = await process_conversation_message(
        db=db,
        agent=agent,
        conversation=conversation,
        user_message_text=request.message,
        source_channel="web",
    )

    return ChatResponse(reply=reply, conversation_id=conversation.id)


@router.post("/transcribe")
async def transcribe_audio_endpoint(
    file: UploadFile = File(...),
    agent_id: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Recibe un archivo de audio y devuelve su transcripción en texto usando el proveedor del agente.
    """
    from services.ai_service import transcribe_audio

    audio_bytes = await file.read()
    mime_type = file.content_type or "audio/webm"
    filename = file.filename or "recording.webm"

    stt_provider = "groq_whisper"
    if agent_id:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if agent and hasattr(agent, "stt_provider") and agent.stt_provider:
            stt_provider = agent.stt_provider

    try:
        text = await transcribe_audio(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            filename=filename,
            stt_provider=stt_provider,
        )
        return {"text": text}
    except Exception as e:
        logger.error(f"Error en endpoint de transcripción: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error transcribiendo audio: {str(e)}"
        )

