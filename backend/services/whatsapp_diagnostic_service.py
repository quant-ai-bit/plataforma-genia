"""
Servicio de Diagnóstico WhatsApp + IA para PLATAFORMA GENIA.

Permite:
1. Obtener la lista de chats/contactos de WhatsApp desde WAHA (store local, sin riesgo).
2. Leer historiales de chat con throttling inteligente para simular scroll manual.
3. Analizar la relación con IA usando el Contexto de Negocio del agente.
4. Detectar apodos ("Don Carlos", "Cami", "Profe") y categorizar contactos.
5. Importar contactos a PreloadedContact (fusión sin sobrescribir datos manuales).
6. Crear Leads automáticos en el Pipeline CRM Kanban con etapa sugerida.
"""

import asyncio
import json
import logging
import random
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

import httpx
from sqlalchemy.orm import Session

from config import settings
from models.agent import Agent
from models.contact import PreloadedContact
from models.lead import Lead
from services.providers.vertex_provider import VertexAIProvider
from services.whatsapp_waha_service import waha_is_mock_mode, _headers, _normalize_phone_number

logger = logging.getLogger(__name__)

# ── Constantes de Throttling Seguro ──
DELAY_BETWEEN_CHATS_MIN = 1.5  # segundos mínimos entre lectura de chats
DELAY_BETWEEN_CHATS_MAX = 3.5  # segundos máximos entre lectura de chats
BATCH_SIZE = 20  # chats por batch
BATCH_PAUSE_SECONDS = 10  # pausa entre batches para no sobrecargar CPU/red

# Progreso global en memoria por agente (agent_id -> status dict)
diagnostic_progress_store: Dict[str, Dict[str, Any]] = {}


async def fetch_whatsapp_contacts(
    session_name: str, limit: int = 50, days_back: int = 90
) -> List[Dict[str, Any]]:
    """
    Obtiene la lista de chats desde la base interna de WAHA.
    Esta operación lee el store local de WAHA y no realiza llamadas externas a WhatsApp.
    """
    if waha_is_mock_mode():
        logger.info("[DIAGNOSTIC] WAHA en modo MOCK. Retornando contactos simulados.")
        return [
            {
                "chat_id": "573001234567@c.us",
                "name": "Carlos Martínez (Don Carlos)",
                "phone": "573001234567",
                "last_message": "Hola, me interesa saber el precio de la oficina privada en Pinares.",
                "last_message_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
                "message_count": 14,
                "is_group": False,
            },
            {
                "chat_id": "573119876543@c.us",
                "name": "Camila López",
                "phone": "573119876543",
                "last_message": "Cami, ¿mañana van a almorzar juntos?",
                "last_message_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                "message_count": 42,
                "is_group": False,
            },
            {
                "chat_id": "573205554433@c.us",
                "name": "Suministros e Insumos Pereira",
                "phone": "573205554433",
                "last_message": "Adjunto factura del aseo de la oficina.",
                "last_message_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
                "message_count": 8,
                "is_group": False,
            },
            {
                "chat_id": "573150001122@c.us",
                "name": "Ingeniero Fernando",
                "phone": "573150001122",
                "last_message": "Fer, te pasé el contacto de un cliente para la sala de juntas.",
                "last_message_at": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
                "message_count": 25,
                "is_group": False,
            },
        ]

    headers = _headers()
    headers["Accept"] = "application/json"
    url = f"{settings.waha_api_url}/api/{session_name}/chats"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.error(f"[DIAGNOSTIC] Error HTTP {resp.status_code} al obtener chats de WAHA: {resp.text}")
                return []

            chats_raw = resp.json()
            if not isinstance(chats_raw, list):
                chats_raw = chats_raw.get("chats", []) if isinstance(chats_raw, dict) else []

            cutoff_timestamp = (datetime.now(timezone.utc) - timedelta(days=days_back)).timestamp()
            processed_contacts = []

            for chat in chats_raw:
                chat_id = str(chat.get("id") or "")
                if not chat_id or "@g.us" in chat_id:  # Filtrar grupos por defecto salvo que se requiera
                    continue

                ts = chat.get("timestamp") or chat.get("messageTimestamp") or 0
                if ts and ts < cutoff_timestamp:
                    continue

                phone = _normalize_phone_number(chat_id)
                name = chat.get("name") or chat.get("pushName") or phone

                last_msg_obj = chat.get("lastMessage") or {}
                last_msg_body = ""
                if isinstance(last_msg_obj, dict):
                    last_msg_body = last_msg_obj.get("body") or last_msg_obj.get("text") or ""
                elif isinstance(last_msg_obj, str):
                    last_msg_body = last_msg_obj

                dt_str = (
                    datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                    if ts
                    else datetime.now(timezone.utc).isoformat()
                )

                processed_contacts.append(
                    {
                        "chat_id": chat_id,
                        "name": name,
                        "phone": phone,
                        "last_message": last_msg_body,
                        "last_message_at": dt_str,
                        "message_count": chat.get("unreadCount", 0) + 1,
                        "is_group": False,
                    }
                )

            # Ordenar por mensaje más reciente y aplicar límite
            processed_contacts.sort(key=lambda c: c["last_message_at"], reverse=True)
            return processed_contacts[:limit]

    except Exception as e:
        logger.error(f"[DIAGNOSTIC] Excepción consultando chats de WAHA: {str(e)}")
        return []


async def fetch_chat_messages(session_name: str, chat_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Obtiene el historial completo de mensajes de un chat específico."""
    if waha_is_mock_mode():
        return [
            {"fromMe": False, "body": "Hola, buenas tardes.", "timestamp": 1722000000},
            {"fromMe": True, "body": "Hola Don Carlos, ¡qué gusto! ¿Cómo estás?", "timestamp": 1722000060},
            {"fromMe": False, "body": "Bien, quería preguntar precio de la oficina en Pinares para 4 personas.", "timestamp": 1722000120},
            {"fromMe": True, "body": "Claro Don Carlos, la oficina de Pinares está disponible en $1.800.000 COP al mes todo incluido.", "timestamp": 1722000180},
        ]

    headers = _headers()
    headers["Accept"] = "application/json"
    url = f"{settings.waha_api_url}/api/{session_name}/chats/{chat_id}/messages?limit={limit}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"[DIAGNOSTIC] No se pudieron obtener mensajes para {chat_id}: {resp.status_code}")
                return []

            msgs_raw = resp.json()
            if not isinstance(msgs_raw, list):
                return []

            formatted = []
            for m in msgs_raw:
                body = m.get("body") or m.get("text") or ""
                if not body:
                    continue
                formatted.append(
                    {
                        "fromMe": m.get("fromMe", False),
                        "body": body,
                        "timestamp": m.get("timestamp", 0),
                    }
                )
            return formatted

    except Exception as e:
        logger.error(f"[DIAGNOSTIC] Error obteniendo mensajes de {chat_id}: {str(e)}")
        return []


async def analyze_contact_with_ai(
    contact: Dict[str, Any],
    messages: List[Dict[str, Any]],
    business_context: Optional[Dict[str, Any]],
    agent: Agent,
) -> Dict[str, Any]:
    """Clasifica la relación del contacto con IA usando Vertex AI gemini-2.5-flash."""
    b_ctx = business_context or getattr(agent, "diagnostic_business_context", {}) or {}

    b_name = b_ctx.get("business_name") or agent.name or "Mi Empresa"
    b_type = b_ctx.get("business_type") or "Servicios Generales"
    b_prods = b_ctx.get("products_services") or "No detallado"
    b_ideal = b_ctx.get("ideal_client") or "No detallado"
    b_sale_kw = ", ".join(b_ctx.get("sale_keywords") or []) or "precio, cotizacion, servicio, comprar"
    b_pers_kw = ", ".join(b_ctx.get("personal_keywords") or []) or "familia, fiesta, almuerzo, mama"
    b_notes = b_ctx.get("additional_notes") or ""

    # Formatear mensajes
    msgs_text = []
    for m in messages:
        sender = "DUEÑO (Tú)" if m.get("fromMe") else "CONTACTO"
        msgs_text.append(f"{sender}: {m.get('body')}")
    formatted_history = "\n".join(msgs_text) if msgs_text else "Sin historial reciente disponible."

    prompt = f"""Eres un experto analista de CRM e Inteligencia Comercial.
Analiza la siguiente conversación de WhatsApp entre el DUEÑO del negocio y un CONTACTO.

═══ CONTEXTO DEL NEGOCIO DEL AGENTE ═══
- Nombre de la Empresa: {b_name}
- Tipo de Negocio / Industria: {b_type}
- Productos/Servicios principales: {b_prods}
- Perfil de Cliente Ideal: {b_ideal}
- Palabras clave de venta: {b_sale_kw}
- Palabras clave personales: {b_pers_kw}
- Notas de contexto: {b_notes}

═══ DATOS DEL CONTACTO ═══
- Nombre registrado en WhatsApp: {contact.get('name')}
- Teléfono: {contact.get('phone')}
- Último mensaje: {contact.get('last_message')}

═══ HISTORIAL RECIENTE DE LA CONVERSACIÓN ═══
{formatted_history}

═══ TAREAS OBLIGATORIAS ═══
1. Clasifica al contacto en EXACTAMENTE UNA de estas 6 categorías:
   - cliente_potencial: Demuestra interés comercial en productos/servicios o pide precios/información.
   - cliente_existente: Ya ha comprado, contratado o mantiene relación comercial activa.
   - aliado_estrategico: Socio, proveedor de referidos, colaborador o contacto clave de negocios.
   - personal: Amigo, familiar, pareja o conocido sin fines comerciales.
   - proveedor: Empresa, vendedor o prestador de servicio que le vende al dueño.
   - irrelevante: Grupos, promociones automatizadas, spam o notificaciones.

2. DETECCIÓN DE APODO / NOMBRE CARIÑOSO (OBLIGATORIO):
   Analiza atentamente las intervenciones del DUEÑO ("DUEÑO (Tú):").
   ¿Cómo llama cariñosa o respetuosamente el dueño a este contacto en la conversación?
   Ejemplos: "Hola Don Carlos" -> "Don Carlos", "Cami te paso la info" -> "Cami", "Hola Profe" -> "Profe", "Doctora Martha" -> "Doctora Martha".
   Si no usa ningún apodo o le habla genéricamente, retorna null.

3. Extrae información comercial clave (si la hay) e indica la etapa CRM sugerida:
   - primer_contacto, en_cualificacion, cualificado, objetivo_cumplido, perdido.

Responde ÚNICAMENTE con una estructura JSON válida con estas claves exactas:
{{
  "category": "cliente_potencial|cliente_existente|aliado_estrategico|personal|proveedor|irrelevante",
  "confidence": 0.95,
  "reason": "Explicación breve de 1 o 2 frases en español sobre la clasificación.",
  "nickname": "Apodo detectado o null",
  "business_data": {{
    "interest": "Interés específico detectado o null",
    "budget": "Presupuesto mencionado o null",
    "last_purchase": "Última transacción o null",
    "interaction_summary": "Resumen conciso del estado actual del chat"
  }},
  "suggested_crm_stage": "primer_contacto|en_cualificacion|cualificado|objetivo_cumplido|perdido"
}}"""

    try:
        vp = VertexAIProvider(model="gemini-2.5-flash")
        response_text = await vp.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )

        # Extraer JSON de la respuesta
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            json_str = match.group(0)
            parsed = json.loads(json_str)
        else:
            parsed = json.loads(response_text)

        category = parsed.get("category", "irrelevante").lower()
        if category not in ["cliente_potencial", "cliente_existente", "aliado_estrategico", "personal", "proveedor", "irrelevante"]:
            category = "irrelevante"

        return {
            "contact": contact,
            "category": category,
            "confidence": float(parsed.get("confidence", 0.8)),
            "reason": parsed.get("reason", "Análisis completado por IA."),
            "nickname": parsed.get("nickname") if parsed.get("nickname") != "null" else None,
            "business_data": parsed.get("business_data", {}),
            "suggested_crm_stage": parsed.get("suggested_crm_stage", "primer_contacto"),
        }

    except Exception as e:
        logger.error(f"[DIAGNOSTIC AI] Error al analizar contacto {contact.get('phone')}: {str(e)}")
        return {
            "contact": contact,
            "category": "irrelevante",
            "confidence": 0.5,
            "reason": f"No se pudo completar el análisis automatizado: {str(e)}",
            "nickname": None,
            "business_data": {},
            "suggested_crm_stage": "primer_contacto",
        }


async def run_diagnostic(
    agent: Agent,
    db: Session,
    selected_chat_ids: Optional[List[str]] = None,
    limit: int = 50,
    days_back: int = 30,
) -> Dict[str, Any]:
    """
    Ejecuta el diagnóstico completo (Modo Manual o Modo Automático) con throttling seguro.
    Actualiza el diccionario de progreso en memoria.
    """
    agent_id = agent.id
    session_name = agent.whatsapp_qr_instance_name or f"genia_{agent_id[:8]}"

    diagnostic_progress_store[agent_id] = {
        "status": "running",
        "progress": 0,
        "current_chat": "Obteniendo contactos...",
        "total_chats": 0,
        "analyzed_chats": 0,
        "estimated_remaining_seconds": 60,
        "results": [],
    }

    try:
        contacts = await fetch_whatsapp_contacts(session_name, limit=limit, days_back=days_back)
        if selected_chat_ids:
            contacts = [c for c in contacts if c["chat_id"] in selected_chat_ids]

        total = len(contacts)
        if total == 0:
            diagnostic_progress_store[agent_id] = {
                "status": "completed",
                "progress": 100,
                "current_chat": "Sin contactos encontrados",
                "total_chats": 0,
                "analyzed_chats": 0,
                "estimated_remaining_seconds": 0,
                "results": [],
            }
            return diagnostic_progress_store[agent_id]

        diagnostic_progress_store[agent_id]["total_chats"] = total

        results = []
        b_context = getattr(agent, "diagnostic_business_context", {}) or {}

        for idx, contact in enumerate(contacts):
            current_name = contact.get("name") or contact.get("phone")
            pct = int(((idx) / total) * 100)
            rem_secs = int((total - idx) * 2.5)

            diagnostic_progress_store[agent_id].update(
                {
                    "progress": pct,
                    "current_chat": f"Analizando {current_name} ({idx + 1}/{total})",
                    "analyzed_chats": idx,
                    "estimated_remaining_seconds": rem_secs,
                }
            )

            # 1. Obtener mensajes completos del chat
            messages = await fetch_chat_messages(session_name, contact["chat_id"], limit=30)

            # 2. Analizar con IA
            analysis = await analyze_contact_with_ai(contact, messages, b_context, agent)
            results.append(analysis)

            # 3. Throttling inteligente entre chats (1.5s - 3.5s)
            if idx < total - 1:
                delay = random.uniform(DELAY_BETWEEN_CHATS_MIN, DELAY_BETWEEN_CHATS_MAX)
                await asyncio.sleep(delay)

                # Pausa adicional por batch cada 20 chats
                if (idx + 1) % BATCH_SIZE == 0:
                    logger.info(f"[DIAGNOSTIC] Batch de {BATCH_SIZE} chats completado. Pausa defensiva de {BATCH_PAUSE_SECONDS}s.")
                    await asyncio.sleep(BATCH_PAUSE_SECONDS)

        # Actualizar estado final en la BD del Agente
        agent.diagnostic_last_run_at = datetime.now(timezone.utc)
        agent.diagnostic_status = "completed"
        db.commit()

        final_data = {
            "status": "completed",
            "progress": 100,
            "current_chat": "Diagnóstico completado exitosamente",
            "total_chats": total,
            "analyzed_chats": total,
            "estimated_remaining_seconds": 0,
            "results": results,
        }
        diagnostic_progress_store[agent_id] = final_data
        return final_data

    except Exception as ex:
        logger.error(f"[DIAGNOSTIC] Fallo durante la ejecución del diagnóstico para el agente {agent_id}: {ex}")
        agent.diagnostic_status = "failed"
        db.commit()
        error_data = {
            "status": "failed",
            "progress": 0,
            "current_chat": f"Error: {str(ex)}",
            "total_chats": 0,
            "analyzed_chats": 0,
            "estimated_remaining_seconds": 0,
            "results": [],
        }
        diagnostic_progress_store[agent_id] = error_data
        return error_data


def import_analyzed_contacts_to_db(
    agent_id: str, analyzed_results: List[Dict[str, Any]], db: Session
) -> Dict[str, Any]:
    """
    Importa/actualiza los contactos analizados como PreloadedContacts.
    Regla de Fusión: Preserva datos manuales precargados y enriquece con WhatsApp/IA.
    """
    created_count = 0
    updated_count = 0

    for item in analyzed_results:
        contact_info = item.get("contact", {})
        phone = contact_info.get("phone")
        if not phone:
            continue

        clean_phone = re.sub(r"\D", "", str(phone))
        if not clean_phone:
            continue

        name = contact_info.get("name") or clean_phone
        nickname = item.get("nickname")
        category = item.get("category")
        confidence = item.get("confidence")
        chat_id = contact_info.get("chat_id")
        last_msg = contact_info.get("last_message")

        existing = (
            db.query(PreloadedContact)
            .filter(
                PreloadedContact.agent_id == agent_id,
                PreloadedContact.phone == clean_phone,
            )
            .first()
        )

        if existing:
            # Enriquecer sin sobrescribir datos manuales válidos
            if nickname:
                existing.nickname = nickname
            existing.ai_category = category
            existing.ai_confidence = confidence
            existing.ai_analysis = item
            existing.whatsapp_chat_id = chat_id
            if last_msg:
                existing.last_message_preview = last_msg[:500]
            updated_count += 1
        else:
            new_contact = PreloadedContact(
                agent_id=agent_id,
                name=name,
                phone=clean_phone,
                nickname=nickname,
                source="whatsapp",
                ai_category=category,
                ai_confidence=confidence,
                ai_analysis=item,
                whatsapp_chat_id=chat_id,
                last_message_preview=last_msg[:500] if last_msg else None,
            )
            db.add(new_contact)
            created_count += 1

    db.commit()
    logger.info(f"[DIAGNOSTIC IMPORT] Agente {agent_id}: {created_count} creados, {updated_count} actualizados.")
    return {"status": "success", "created": created_count, "updated": updated_count}


def create_leads_from_diagnostic_results(
    agent_id: str, analyzed_results: List[Dict[str, Any]], db: Session
) -> Dict[str, Any]:
    """Crea automáticamente leads en el CRM Kanban a partir de los contactos clasificados."""
    created_leads = 0
    updated_leads = 0

    for item in analyzed_results:
        category = item.get("category", "")
        if category not in ["cliente_potencial", "cliente_existente", "aliado_estrategico"]:
            continue

        contact_info = item.get("contact", {})
        phone = contact_info.get("phone")
        if not phone:
            continue

        clean_phone = re.sub(r"\D", "", str(phone))
        name = contact_info.get("name") or clean_phone
        nickname = item.get("nickname")
        stage = item.get("suggested_crm_stage") or "primer_contacto"
        b_data = item.get("business_data") or {}

        # Mapeo de categoría a stage si no viene especificado
        if category == "cliente_existente":
            stage = "cualificado"
        elif category == "aliado_estrategico":
            stage = "en_cualificacion"

        # Verificar si ya existe lead por teléfono para este agente
        existing_lead = (
            db.query(Lead)
            .filter(
                Lead.agent_id == agent_id,
                Lead.phone == clean_phone,
            )
            .first()
        )

        custom_data_payload = {
            "source": "diagnostic_whatsapp",
            "nickname": nickname,
            "ai_category": category,
            "interest": b_data.get("interest"),
            "budget": b_data.get("budget"),
            "summary": b_data.get("interaction_summary") or item.get("reason"),
        }

        if existing_lead:
            existing_lead.status = stage
            current_custom = existing_lead.custom_data or {}
            current_custom.update({k: v for k, v in custom_data_payload.items() if v})
            existing_lead.custom_data = current_custom
            updated_leads += 1
        else:
            new_lead = Lead(
                agent_id=agent_id,
                name=f"{name} ({nickname})" if nickname else name,
                phone=clean_phone,
                source_channel="whatsapp",
                status=stage,
                custom_data=custom_data_payload,
            )
            db.add(new_lead)
            created_leads += 1

    db.commit()
    logger.info(f"[DIAGNOSTIC PIPELINE] Agente {agent_id}: {created_leads} leads creados, {updated_leads} actualizados.")
    return {"status": "success", "created_leads": created_leads, "updated_leads": updated_leads}
