"""
Servicio de integración con Google Calendar para PLATAFORMA GENIA.

Permite a cada agente conectar su propio Google Calendar via OAuth 2.0
y expone funciones para consultar, crear, cancelar, reprogramar eventos
y enviar recordatorios.

Las credenciales (refresh tokens) se almacenan cifradas con Fernet (AES-256)
por agente en la base de datos.
"""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from config import settings
from services.encryption_service import encrypt, decrypt

logger = logging.getLogger(__name__)

# Scopes requeridos para lectura/escritura de Calendar
CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]


def _get_client_config(agent) -> dict:
    """Construye la configuración de cliente OAuth para el agente."""
    client_id = agent.google_calendar_client_id or settings.google_calendar_client_id
    
    client_secret = ""
    if agent.google_calendar_client_secret:
        client_secret = decrypt(agent.google_calendar_client_secret)
    else:
        client_secret = settings.google_calendar_client_secret

    if not client_id or not client_secret:
        raise ValueError(
            "Google Calendar Client ID y Client Secret no están configurados para este agente. "
            "Por favor, ingrésalos en la configuración de la integración."
        )
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_calendar_redirect_uri],
        }
    }


def get_auth_url(agent_id: str, db, base_url: str = "") -> str:
    """
    Genera la URL de autorización OAuth 2.0 para conectar Google Calendar.

    Args:
        agent_id: ID del agente que se está conectando.
        db: Sesión de base de datos.
        base_url: URL base de la aplicación.

    Returns:
        URL de autorización de Google para que el usuario inicie sesión.
    """
    from models.agent import Agent
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise ValueError("Agente no encontrado.")

    redirect_uri = settings.google_calendar_redirect_uri
    if not redirect_uri and base_url:
        redirect_uri = f"{base_url}/api/calendar/{agent_id}/callback"

    flow = Flow.from_client_config(
        _get_client_config(agent),
        scopes=CALENDAR_SCOPES,
        redirect_uri=redirect_uri,
    )

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=agent_id,
    )

    return auth_url


def handle_callback(agent_id: str, auth_code: str, db) -> dict:
    """
    Intercambia el código de autorización por tokens OAuth y los almacena cifrados.

    Args:
        agent_id: ID del agente.
        auth_code: Código de autorización recibido de Google.
        db: Sesión de base de datos.

    Returns:
        dict con claves: connected, email, error.
    """
    from models.agent import Agent
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        return {"connected": False, "email": None, "error": "Agente no encontrado."}

    try:
        flow = Flow.from_client_config(
            _get_client_config(agent),
            scopes=CALENDAR_SCOPES,
            redirect_uri=settings.google_calendar_redirect_uri,
        )

        flow.fetch_token(code=auth_code)
        credentials = flow.credentials

        if not credentials or not credentials.refresh_token:
            return {
                "connected": False,
                "email": None,
                "error": "No se obtuvo un refresh token. Intenta desconectar y reconectar.",
            }

        # Obtener email del usuario autenticado
        email = _get_user_email(credentials)

        # Cifrar y almacenar refresh token
        agent.google_calendar_refresh_token = encrypt(credentials.refresh_token)
        agent.google_calendar_connected = True
        agent.google_calendar_email = email

        # Asegurar que 'google_calendar' esté en los canales
        channels = agent.channels or []
        if "google_calendar" not in channels:
            agent.channels = channels + ["google_calendar"]

        db.commit()

        logger.info(
            "Google Calendar conectado exitosamente para agente '%s' (email=%s).",
            agent.name,
            email,
        )

        return {"connected": True, "email": email, "error": None}

    except Exception as e:
        logger.error("Error en callback de Google Calendar: %s", str(e), exc_info=True)
        return {"connected": False, "email": None, "error": str(e)}


def disconnect_calendar(agent_id: str, db) -> dict:
    """Desconecta Google Calendar de un agente, revocando y limpiando tokens."""
    from models.agent import Agent

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        return {"status": "error", "message": "Agente no encontrado."}

    # Intentar revocar el token en Google
    if agent.google_calendar_refresh_token:
        try:
            refresh_token = decrypt(agent.google_calendar_refresh_token)
            if refresh_token:
                httpx.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": refresh_token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        except Exception as e:
            logger.warning("Error revocando token de Calendar: %s", str(e))

    agent.google_calendar_refresh_token = None
    agent.google_calendar_connected = False
    agent.google_calendar_email = None

    db.commit()

    logger.info("Google Calendar desconectado del agente '%s'.", agent.name)
    return {"status": "disconnected", "message": "Google Calendar desconectado."}


def _get_credentials_for_agent(agent_id: str, db) -> Credentials | None:
    """Recupera y refresca las credenciales OAuth para un agente."""
    from models.agent import Agent

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or not agent.google_calendar_refresh_token:
        return None

    refresh_token = decrypt(agent.google_calendar_refresh_token)
    if not refresh_token:
        return None

    client_id = agent.google_calendar_client_id or settings.google_calendar_client_id
    client_secret = ""
    if agent.google_calendar_client_secret:
        client_secret = decrypt(agent.google_calendar_client_secret)
    else:
        client_secret = settings.google_calendar_client_secret

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=CALENDAR_SCOPES,
    )

    # Refrescar si es necesario
    if not credentials.valid:
        from google.auth.transport.requests import Request
        try:
            credentials.refresh(Request())
        except Exception as e:
            logger.error(
                "Error refrescando credenciales de Calendar para agente %s: %s",
                agent_id, str(e),
            )
            return None

    return credentials


def _get_calendar_service(agent_id: str, db):
    """Construye y retorna el servicio de Google Calendar API."""
    credentials = _get_credentials_for_agent(agent_id, db)
    if not credentials:
        raise ValueError(
            f"No se pudieron obtener credenciales de Calendar para el agente {agent_id}."
        )
    return build("calendar", "v3", credentials=credentials)


def _get_user_email(credentials: Credentials) -> str:
    """Obtiene el email del usuario autenticado usando la API de userinfo."""
    try:
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        return user_info.get("email", "desconocido")
    except Exception as e:
        logger.warning("No se pudo obtener email de Calendar: %s", str(e))
        return "desconocido"


# ─── Funciones de Calendar para Function-Calling del agente ──────────


async def list_events(
    agent_id: str,
    db,
    time_min: str | None = None,
    time_max: str | None = None,
    max_results: int = 10,
    timezone_str: str = "America/Bogota",
) -> list[dict]:
    """
    Lista eventos del calendario del agente.

    Args:
        agent_id: ID del agente.
        db: Sesión de base de datos.
        time_min: Inicio del rango (ISO 8601). Default: ahora.
        time_max: Fin del rango (ISO 8601). Default: 7 días adelante.
        max_results: Máximo de resultados.
        timezone_str: Zona horaria para la consulta.

    Returns:
        Lista de eventos con campos: id, title, start, end, attendees, location.
    """
    service = _get_calendar_service(agent_id, db)
    tz = ZoneInfo(timezone_str)

    if not time_min:
        time_min = datetime.now(tz).isoformat()
    if not time_max:
        time_max = (datetime.now(tz) + timedelta(days=7)).isoformat()

    events_result = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
        timeZone=timezone_str,
    ).execute()

    events = events_result.get("items", [])
    return [
        {
            "id": event["id"],
            "title": event.get("summary", "Sin título"),
            "start": event["start"].get("dateTime", event["start"].get("date")),
            "end": event["end"].get("dateTime", event["end"].get("date")),
            "attendees": [
                a.get("email", "") for a in event.get("attendees", [])
            ],
            "location": event.get("location", ""),
            "description": event.get("description", ""),
            "status": event.get("status", "confirmed"),
        }
        for event in events
    ]


async def check_availability(
    agent_id: str,
    db,
    date: str,
    timezone_str: str = "America/Bogota",
    working_hours_start: int = 8,
    working_hours_end: int = 18,
    slot_duration_minutes: int = 60,
) -> dict:
    """
    Verifica la disponibilidad del calendario para una fecha determinada.

    Retorna las franjas horarias disponibles dentro del horario laboral.
    """
    tz = ZoneInfo(timezone_str)
    target_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=tz)

    time_min = target_date.replace(hour=working_hours_start, minute=0, second=0).isoformat()
    time_max = target_date.replace(hour=working_hours_end, minute=0, second=0).isoformat()

    busy_events = await list_events(
        agent_id=agent_id,
        db=db,
        time_min=time_min,
        time_max=time_max,
        max_results=50,
        timezone_str=timezone_str,
    )

    # Calcular franjas ocupadas
    busy_slots = []
    for event in busy_events:
        if event["status"] == "cancelled":
            continue
        start = datetime.fromisoformat(event["start"])
        end = datetime.fromisoformat(event["end"])
        busy_slots.append((start, end))

    # Generar franjas disponibles
    available_slots = []
    current = target_date.replace(hour=working_hours_start, minute=0, second=0)
    end_of_day = target_date.replace(hour=working_hours_end, minute=0, second=0)

    while current < end_of_day:
        slot_end = current + timedelta(minutes=slot_duration_minutes)
        is_free = True
        for busy_start, busy_end in busy_slots:
            if current < busy_end and slot_end > busy_start:
                is_free = False
                break
        if is_free:
            available_slots.append({
                "start": current.strftime("%H:%M"),
                "end": slot_end.strftime("%H:%M"),
            })
        current = slot_end

    return {
        "date": date,
        "timezone": timezone_str,
        "total_available_slots": len(available_slots),
        "available_slots": available_slots,
        "busy_events_count": len([e for e in busy_events if e["status"] != "cancelled"]),
    }


async def create_event(
    agent_id: str,
    db,
    summary: str,
    start_datetime: str,
    end_datetime: str,
    timezone_str: str = "America/Bogota",
    attendee_name: str = "",
    attendee_email: str = "",
    description: str = "",
    location: str = "",
) -> dict:
    """
    Crea un evento en el calendario del agente.

    Args:
        agent_id: ID del agente.
        db: Sesión de base de datos.
        summary: Título del evento.
        start_datetime: Inicio en formato ISO 8601.
        end_datetime: Fin en formato ISO 8601.
        timezone_str: Zona horaria.
        attendee_name: Nombre del asistente (opcional).
        attendee_email: Email del asistente (opcional).
        description: Descripción del evento (opcional).
        location: Ubicación del evento (opcional).

    Returns:
        dict con el evento creado: id, title, start, end, link.
    """
    service = _get_calendar_service(agent_id, db)

    event_body = {
        "summary": summary,
        "description": description or f"Cita agendada por el agente de IA. Cliente: {attendee_name}",
        "location": location,
        "start": {
            "dateTime": start_datetime,
            "timeZone": timezone_str,
        },
        "end": {
            "dateTime": end_datetime,
            "timeZone": timezone_str,
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 30},
                {"method": "email", "minutes": 60},
            ],
        },
    }

    if attendee_email:
        event_body["attendees"] = [
            {"email": attendee_email, "displayName": attendee_name},
        ]

    created_event = service.events().insert(
        calendarId="primary",
        body=event_body,
        sendUpdates="all" if attendee_email else "none",
    ).execute()

    logger.info(
        "Evento creado en Calendar del agente '%s': %s (%s a %s)",
        agent_id,
        summary,
        start_datetime,
        end_datetime,
    )

    return {
        "id": created_event["id"],
        "title": created_event.get("summary", ""),
        "start": start_datetime,
        "end": end_datetime,
        "link": created_event.get("htmlLink", ""),
        "status": "confirmed",
    }


async def cancel_event(
    agent_id: str,
    db,
    event_id: str,
    cancellation_reason: str = "",
) -> dict:
    """
    Cancela un evento del calendario.

    Args:
        agent_id: ID del agente.
        db: Sesión de base de datos.
        event_id: ID del evento a cancelar.
        cancellation_reason: Motivo de la cancelación.

    Returns:
        dict con estado de la cancelación.
    """
    service = _get_calendar_service(agent_id, db)

    try:
        # Primero obtener el evento para añadir nota de cancelación
        event = service.events().get(calendarId="primary", eventId=event_id).execute()
        existing_desc = event.get("description", "")
        cancel_note = f"\n\n[CANCELADO] Motivo: {cancellation_reason}" if cancellation_reason else "\n\n[CANCELADO]"
        event["description"] = existing_desc + cancel_note

        # Actualizar descripción y luego cancelar
        service.events().update(
            calendarId="primary",
            eventId=event_id,
            body=event,
            sendUpdates="all",
        ).execute()

        service.events().delete(
            calendarId="primary",
            eventId=event_id,
            sendUpdates="all",
        ).execute()

        logger.info(
            "Evento %s cancelado en Calendar del agente '%s'. Motivo: %s",
            event_id,
            agent_id,
            cancellation_reason,
        )

        return {
            "status": "cancelled",
            "event_id": event_id,
            "title": event.get("summary", ""),
            "reason": cancellation_reason,
        }
    except Exception as e:
        logger.error("Error cancelando evento %s: %s", event_id, str(e))
        return {"status": "error", "error": str(e)}


async def reschedule_event(
    agent_id: str,
    db,
    event_id: str,
    new_start: str,
    new_end: str,
    timezone_str: str = "America/Bogota",
) -> dict:
    """
    Reprograma un evento existente a una nueva fecha/hora.

    Args:
        agent_id: ID del agente.
        db: Sesión de base de datos.
        event_id: ID del evento a reprogramar.
        new_start: Nueva fecha/hora de inicio (ISO 8601).
        new_end: Nueva fecha/hora de fin (ISO 8601).
        timezone_str: Zona horaria.

    Returns:
        dict con el evento actualizado.
    """
    service = _get_calendar_service(agent_id, db)

    try:
        event = service.events().get(calendarId="primary", eventId=event_id).execute()

        event["start"] = {"dateTime": new_start, "timeZone": timezone_str}
        event["end"] = {"dateTime": new_end, "timeZone": timezone_str}

        existing_desc = event.get("description", "")
        event["description"] = existing_desc + f"\n\n[REPROGRAMADO] Nueva hora: {new_start} - {new_end}"

        updated_event = service.events().update(
            calendarId="primary",
            eventId=event_id,
            body=event,
            sendUpdates="all",
        ).execute()

        logger.info(
            "Evento %s reprogramado en Calendar del agente '%s': %s a %s",
            event_id,
            agent_id,
            new_start,
            new_end,
        )

        return {
            "status": "rescheduled",
            "event_id": event_id,
            "title": updated_event.get("summary", ""),
            "new_start": new_start,
            "new_end": new_end,
            "link": updated_event.get("htmlLink", ""),
        }
    except Exception as e:
        logger.error("Error reprogramando evento %s: %s", event_id, str(e))
        return {"status": "error", "error": str(e)}


async def get_event_details(
    agent_id: str,
    db,
    event_id: str,
) -> dict:
    """Obtiene los detalles completos de un evento específico."""
    service = _get_calendar_service(agent_id, db)

    try:
        event = service.events().get(calendarId="primary", eventId=event_id).execute()
        return {
            "id": event["id"],
            "title": event.get("summary", "Sin título"),
            "start": event["start"].get("dateTime", event["start"].get("date")),
            "end": event["end"].get("dateTime", event["end"].get("date")),
            "attendees": [a.get("email", "") for a in event.get("attendees", [])],
            "location": event.get("location", ""),
            "description": event.get("description", ""),
            "status": event.get("status", "confirmed"),
            "link": event.get("htmlLink", ""),
        }
    except Exception as e:
        logger.error("Error obteniendo evento %s: %s", event_id, str(e))
        return {"status": "error", "error": str(e)}


async def get_upcoming_for_reminder(
    agent_id: str,
    db,
    hours_ahead: int = 24,
    timezone_str: str = "America/Bogota",
) -> list[dict]:
    """
    Obtiene eventos próximos para enviar recordatorios/reconfirmaciones.

    Args:
        agent_id: ID del agente.
        db: Sesión de base de datos.
        hours_ahead: Horas hacia adelante para buscar eventos.
        timezone_str: Zona horaria.

    Returns:
        Lista de eventos próximos con info de asistentes.
    """
    tz = ZoneInfo(timezone_str)
    now = datetime.now(tz)
    time_max = (now + timedelta(hours=hours_ahead)).isoformat()

    return await list_events(
        agent_id=agent_id,
        db=db,
        time_min=now.isoformat(),
        time_max=time_max,
        max_results=20,
        timezone_str=timezone_str,
    )
