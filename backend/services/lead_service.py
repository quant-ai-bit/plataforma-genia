"""
Servicio de gestión de Leads para PLATAFORMA GENIA.

Proporciona funciones para extraer, crear y actualizar leads
a partir de los datos capturados automáticamente por el
function-calling del servicio de IA.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.lead import Lead

logger = logging.getLogger(__name__)


def extract_and_save_lead(
    db: Session,
    agent_id: str,
    conversation_id: str,
    lead_data: dict,
    source_channel: str = "web",
) -> Lead:
    """
    Extrae datos de lead y los guarda (o actualiza) en la base de datos.

    Si ya existe un lead asociado al ``conversation_id``, actualiza solo los
    campos que traigan valores nuevos (no sobrescribe con vacíos).
    Si no existe, crea un nuevo registro.

    Para ``custom_data``, se hace merge acumulativo: los campos existentes
    se conservan y los nuevos se agregan o actualizan.

    Args:
        db: sesión activa de SQLAlchemy.
        agent_id: UUID del agente al que pertenece el lead.
        conversation_id: UUID de la conversación que originó el lead.
        lead_data: diccionario con los datos capturados (ej. ``{"name": "...", "business_type": "..."}``).
        source_channel: canal de origen (``"web"``, ``"whatsapp"``, ``"instagram"``, etc.).

    Returns:
        Instancia del modelo ``Lead`` guardada/actualizada.
    """
    # ── Separar campos estándar de campos personalizados ──────────
    lead_name: str = lead_data.get("name", "")
    lead_email: str = lead_data.get("email", "")
    lead_phone: str = lead_data.get("phone", "")

    # Todo lo que no sea un campo estándar se considera custom_data
    standard_fields = {"name", "email", "phone"}
    custom_data_new: dict = {
        k: v for k, v in lead_data.items() if k not in standard_fields
    }

    # ── Buscar lead existente por conversation_id ────────────────
    existing_lead: Lead | None = (
        db.query(Lead)
        .filter(Lead.conversation_id == conversation_id)
        .first()
    )

    if existing_lead:
        logger.info(
            "Actualizando lead existente (id=%s) para conversación %s",
            existing_lead.id,
            conversation_id,
        )

        # Actualizar solo campos con valor (no sobrescribir con vacío)
        if lead_name:
            existing_lead.name = lead_name
        if lead_email:
            existing_lead.email = lead_email
        if lead_phone:
            existing_lead.phone = lead_phone

        # Merge acumulativo de custom_data
        current_custom: dict = existing_lead.custom_data or {}
        current_custom.update(custom_data_new)
        existing_lead.custom_data = current_custom

        existing_lead.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(existing_lead)

        logger.info("Lead actualizado correctamente: %s", existing_lead.id)
        return existing_lead

    else:
        logger.info(
            "Creando nuevo lead para conversación %s del agente %s",
            conversation_id,
            agent_id,
        )

        new_lead = Lead(
            agent_id=agent_id,
            conversation_id=conversation_id,
            name=lead_name or None,
            email=lead_email or None,
            phone=lead_phone or None,
            source_channel=source_channel,
            custom_data=custom_data_new if custom_data_new else None,
        )

        db.add(new_lead)
        db.commit()
        db.refresh(new_lead)

        logger.info("Lead creado correctamente: %s", new_lead.id)
        return new_lead


async def check_lead_completeness_and_notify(
    db: Session,
    lead_id: str,
) -> bool:
    """
    Verifica si el lead con ``lead_id`` tiene todos los campos obligatorios
    del agente completos. Si está completo y la conversación no ha sido
    notificada, envía un mensaje por WhatsApp al encargado del agente
    y marca ``conversation.lead_notified = True``.
    """
    from models.agent import Agent
    from models.conversation import Conversation
    from services.whatsapp_service import send_whatsapp_notification
    from services.encryption_service import decrypt as _decrypt

    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        logger.warning("No se encontró el lead con ID %s para verificación de notificación.", lead_id)
        return False

    conversation = db.query(Conversation).filter(Conversation.id == lead.conversation_id).first()
    agent = db.query(Agent).filter(Agent.id == lead.agent_id).first()

    if not agent or not conversation:
        logger.warning("Falta agente o conversación para el lead %s.", lead_id)
        return False

    # Si ya se notificó, no hacer nada
    if conversation.lead_notified:
        return False

    # Si el agente no tiene teléfono de notificación configurado, no hacer nada
    if not agent.notification_phone:
        logger.info("Agente %s no tiene notification_phone configurado. Omitiendo notificación.", agent.id)
        return False

    # Obtener campos requeridos del agente
    custom_fields = agent.custom_fields or []
    required_fields = []
    for field in custom_fields:
        if isinstance(field, dict) and field.get("required"):
            required_fields.append({
                "key": field.get("key"),
                "label": field.get("label", field.get("key"))
            })

    # Si el agente no tiene campos requeridos configurados, no podemos definir si está "completo".
    if not required_fields:
        return False

    # Obtener valores actuales del lead
    lead_values = {
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
    }
    if lead.custom_data:
        lead_values.update(lead.custom_data)

    # Validar que todos los campos requeridos estén completos
    missing_fields = []
    for f in required_fields:
        val = lead_values.get(f["key"])
        if val is None or str(val).strip() == "":
            missing_fields.append(f["label"])

    if missing_fields:
        logger.info("Lead %s incompleto. Faltan campos obligatorios: %s", lead_id, missing_fields)
        return False

    # ¡El lead está completo! Generar el resumen de los campos configurados del agente
    captured_summary = []
    for field in custom_fields:
        if isinstance(field, dict):
            key = field.get("key")
            label = field.get("label", key)
            val = lead_values.get(key)
            if val is not None and str(val).strip() != "":
                captured_summary.append(f"• *{label}*: {val}")

    summary_text = "\n".join(captured_summary)
    
    # Formatear el mensaje para el encargado
    message_text = (
        f"✅ *¡Lead Completado con Éxito!*\n\n"
        f"El agente *{agent.name}* ha finalizado la captura de datos con el cliente.\n\n"
        f"*Datos Capturados:*\n{summary_text}\n\n"
        f"Canal: {lead.source_channel.upper()}\n"
        f"ID Conversación: `{conversation.id}`"
    )

    # Enviar notificación de WhatsApp (usando credenciales del agente)
    _phone_id = agent.whatsapp_phone_number_id or ""
    _token = _decrypt(agent.whatsapp_access_token) if agent.whatsapp_access_token else ""
    success = await send_whatsapp_notification(
        agent.notification_phone, message_text,
        phone_number_id=_phone_id, access_token=_token,
    )
    if success:
        conversation.lead_notified = True
        db.commit()
        logger.info("Notificación de lead completado enviada y guardada para conversación %s", conversation.id)
        return True
    
    return False
