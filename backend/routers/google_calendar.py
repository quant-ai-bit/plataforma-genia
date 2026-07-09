"""
Router de Google Calendar para PLATAFORMA GENIA.

Gestiona la conexión OAuth 2.0 de Google Calendar por agente,
consultando estado de conexión, listado de eventos y desconexión.

Cada agente conecta su propio Google Calendar del negocio.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models.agent import Agent
from services.auth_service import get_current_user
from services import google_calendar_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calendar", tags=["Google Calendar Integration"])


@router.get("/{agent_id}/auth-url")
async def get_calendar_auth_url(
    agent_id: str,
    base_url: str = Query("", description="URL base de la aplicación para construir el redirect_uri"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Genera la URL de autorización OAuth 2.0 de Google Calendar.

    El usuario del dashboard debe ser redirigido a esta URL para autorizar
    el acceso a su Google Calendar.
    """
    # Verificar que el agente pertenece al usuario
    query = db.query(Agent).filter(Agent.id == agent_id)
    if current_user["id"] != "local_dev_user":
        query = query.filter(Agent.user_id == current_user["id"])

    agent = query.first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agente {agent_id} no encontrado.",
        )

    try:
        auth_url = google_calendar_service.get_auth_url(
            agent_id=agent_id,
            db=db,
            base_url=base_url,
        )
        return {"auth_url": auth_url, "agent_id": agent_id}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{agent_id}/callback")
async def calendar_oauth_callback(
    agent_id: str,
    code: str = Query(..., description="Código de autorización de Google OAuth"),
    state: str = Query("", description="Estado de seguridad (agent_id)"),
    db: Session = Depends(get_db),
):
    """
    Callback de Google OAuth 2.0.

    Recibe el código de autorización, lo intercambia por tokens
    y los almacena cifrados para el agente.

    NOTA: Este endpoint NO requiere autenticación JWT porque Google
    redirige al usuario directamente aquí.
    """
    # Usar state como agent_id si viene (para seguridad)
    effective_agent_id = state if state else agent_id

    result = google_calendar_service.handle_callback(
        agent_id=effective_agent_id,
        auth_code=code,
        db=db,
    )

    if result["connected"]:
        # Retornar HTML que cierre la ventana popup o redirija al dashboard
        return _build_success_html(effective_agent_id, result["email"])
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error conectando Google Calendar: {result['error']}",
        )


@router.get("/{agent_id}/status")
async def get_calendar_status(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Retorna el estado de conexión de Google Calendar para un agente.
    """
    query = db.query(Agent).filter(Agent.id == agent_id)
    if current_user["id"] != "local_dev_user":
        query = query.filter(Agent.user_id == current_user["id"])

    agent = query.first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agente {agent_id} no encontrado.",
        )

    return {
        "connected": agent.google_calendar_connected or False,
        "email": agent.google_calendar_email,
    }


@router.post("/{agent_id}/disconnect")
async def disconnect_calendar(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Desconecta Google Calendar de un agente, revocando tokens.
    """
    query = db.query(Agent).filter(Agent.id == agent_id)
    if current_user["id"] != "local_dev_user":
        query = query.filter(Agent.user_id == current_user["id"])

    agent = query.first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agente {agent_id} no encontrado.",
        )

    result = google_calendar_service.disconnect_calendar(agent_id=agent_id, db=db)
    return result


@router.get("/{agent_id}/events")
async def list_calendar_events(
    agent_id: str,
    days: int = Query(7, ge=1, le=30, description="Número de días hacia adelante"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Lista los próximos eventos del calendario del agente.
    """
    query = db.query(Agent).filter(Agent.id == agent_id)
    if current_user["id"] != "local_dev_user":
        query = query.filter(Agent.user_id == current_user["id"])

    agent = query.first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agente {agent_id} no encontrado.",
        )

    if not agent.google_calendar_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google Calendar no está conectado para este agente.",
        )

    try:
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo

        tz_str = agent.timezone or "America/Bogota"
        tz = ZoneInfo(tz_str)
        now = datetime.now(tz)

        events = await google_calendar_service.list_events(
            agent_id=agent_id,
            db=db,
            time_min=now.isoformat(),
            time_max=(now + timedelta(days=days)).isoformat(),
            timezone_str=tz_str,
        )
        return {"events": events, "timezone": tz_str}
    except Exception as e:
        logger.error("Error listando eventos de Calendar: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo eventos: {str(e)}",
        )


@router.get("/stt-providers")
async def list_stt_providers():
    """
    Retorna la lista de proveedores STT disponibles.
    Útil para poblar el selector en la configuración del agente.
    """
    from services.stt_service import get_available_providers
    return {"providers": get_available_providers()}


# ─── Helpers ────────────────────────────────────────────────────────


def _build_success_html(agent_id: str, email: str) -> dict:
    """
    Retorna un HTML que muestra éxito y cierra la ventana popup o redirige.
    Por ahora retorna JSON ya que el frontend maneja la redirección.
    """
    from fastapi.responses import HTMLResponse

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Google Calendar Conectado</title>
        <style>
            body {{
                font-family: 'Inter', sans-serif;
                background: #0f1117;
                color: #e5e7eb;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }}
            .card {{
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 16px;
                padding: 40px;
                text-align: center;
                backdrop-filter: blur(20px);
            }}
            .success {{ color: #22c55e; font-size: 48px; }}
            h2 {{ margin: 16px 0 8px; }}
            p {{ color: #9ca3af; }}
            .email {{ color: #60a5fa; font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="success">✅</div>
            <h2>Google Calendar Conectado</h2>
            <p>Calendario de <span class="email">{email}</span> conectado exitosamente.</p>
            <p>Puedes cerrar esta ventana y volver al dashboard.</p>
            <script>
                // Si se abrió como popup, cerrar automáticamente
                setTimeout(() => {{
                    if (window.opener) {{
                        window.opener.postMessage({{
                            type: 'calendar_connected',
                            agentId: '{agent_id}',
                            email: '{email}'
                        }}, '*');
                        window.close();
                    }}
                }}, 2000);
            </script>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)
