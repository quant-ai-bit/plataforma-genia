"""
Router Wasi.co para PLATAFORMA GENIA.

Endpoints para conectar, sincronizar y desconectar la integración del agente
con el inventario inmobiliario de Wasi.co.

Endpoints:
  POST /wasi/connect          - Guarda y verifica credenciales Wasi del agente.
  GET  /wasi/status           - Retorna estado de conexión + métricas del inventario.
  POST /wasi/sync             - Sincroniza el inventario activo al RAG del agente.
  POST /wasi/disconnect       - Desconecta la integración Wasi del agente.
  POST /wasi/search-properties - (Debugging) Busca propiedades con filtros.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.agent import Agent
from services.auth_service import get_current_user
from services import wasi_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wasi", tags=["Wasi.co Integration"])


# ── Helpers ───────────────────────────────────────────────────────────

def _get_agent_or_404(db: Session, agent_id: str, current_user: dict) -> Agent:
    """Retorna el agente si pertenece al usuario o lanza 404."""
    import os
    env = os.getenv("ENVIRONMENT", "development")
    user_id = current_user.get("id") if isinstance(current_user, dict) else "local_dev_user"

    if user_id and user_id != "local_dev_user":
        orphan = db.query(Agent).filter(
            (Agent.id == agent_id) & ((Agent.user_id == None) | (Agent.user_id == "local_dev_user"))
        ).first()
        if orphan:
            orphan.user_id = user_id
            db.commit()
            db.refresh(orphan)

    query = db.query(Agent).filter(Agent.id == agent_id)
    if user_id and user_id != "local_dev_user":
        agent = query.filter(Agent.user_id == user_id).first()
        if not agent:
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if agent and env == "development":
                agent.user_id = user_id
                db.commit()
                db.refresh(agent)
    else:
        agent = query.first()

    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agente no encontrado.")
    return agent


def _encrypt(value: str) -> str:
    """Cifra un valor con Fernet para almacenamiento seguro."""
    try:
        from services.encryption_service import encrypt
        return encrypt(value)
    except ImportError:
        logger.warning("encryption_service no disponible, guardando sin cifrar.")
        return value


def _decrypt(value: str) -> str:
    """Descifra un valor Fernet."""
    try:
        from services.encryption_service import decrypt
        return decrypt(value)
    except ImportError:
        return value


# ── Schemas de Request/Response ───────────────────────────────────────

class WasiConnectRequest(BaseModel):
    company_id: str = Field(..., min_length=1, description="ID de empresa en Wasi.co")
    wasi_token: str = Field(..., min_length=10, description="Token de acceso API Wasi.co")

class WasiSearchRequest(BaseModel):
    tipo_propiedad: str | None = Field(default=None, description="Ej: Apartamento, Casa, Lote / Terreno")
    proposito: str | None = Field(default=None, description="Vivir, Inversión, Arrendar")
    presupuesto_min: int | None = Field(default=None, ge=0)
    presupuesto_max: int | None = Field(default=None, ge=0)
    zona: str | None = Field(default=None, description="Zona, ciudad o barrio de interés")
    max_resultados: int = Field(default=3, ge=1, le=5)


# ── Endpoints ─────────────────────────────────────────────────────────

@router.post("/connect/{agent_id}")
async def connect_wasi(
    agent_id: str,
    payload: WasiConnectRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Guarda las credenciales Wasi del agente y verifica su validez.
    Las credenciales se almacenan cifradas con Fernet.
    """
    agent = _get_agent_or_404(db, agent_id, current_user)

    # 1. Validar credenciales con Wasi API
    is_valid = await wasi_service.validate_credentials(payload.company_id, payload.wasi_token)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Las credenciales de Wasi no son válidas. "
                "Verifica el ID de empresa y el token en tu cuenta de Wasi.co."
            ),
        )

    # 2. Guardar credenciales cifradas
    agent.wasi_company_id = payload.company_id
    agent.wasi_token = _encrypt(payload.wasi_token)
    agent.wasi_connected = True
    agent.wasi_sync_status = "idle"
    db.commit()
    db.refresh(agent)

    logger.info("Wasi conectado para agente %s (company=%s)", agent_id, payload.company_id)
    return {
        "status": "connected",
        "message": "Wasi.co conectado correctamente. Puedes sincronizar el inventario ahora.",
        "company_id": agent.wasi_company_id,
        "wasi_connected": agent.wasi_connected,
    }


@router.get("/status/{agent_id}")
async def get_wasi_status(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Retorna el estado de la integración Wasi del agente:
    conexión, última sincronización y total de propiedades en RAG.
    """
    agent = _get_agent_or_404(db, agent_id, current_user)
    return {
        "wasi_connected": agent.wasi_connected or False,
        "wasi_company_id": agent.wasi_company_id,
        "wasi_sync_status": agent.wasi_sync_status or "idle",
        "wasi_last_sync_at": (
            agent.wasi_last_sync_at.isoformat() if agent.wasi_last_sync_at else None
        ),
        "wasi_properties_count": agent.wasi_properties_count or 0,
    }


@router.post("/sync/{agent_id}")
async def sync_wasi_inventory(
    agent_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Dispara la sincronización del inventario activo de Wasi al RAG del agente.
    La sincronización se ejecuta en background (no bloquea la UI).
    """
    agent = _get_agent_or_404(db, agent_id, current_user)

    if not agent.wasi_connected or not agent.wasi_company_id or not agent.wasi_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primero conecta Wasi.co con credenciales válidas.",
        )

    if agent.wasi_sync_status == "syncing":
        return {"status": "already_syncing", "message": "La sincronización ya está en progreso."}

    # Marcar como sincronizando inmediatamente
    agent.wasi_sync_status = "syncing"
    db.commit()

    async def _do_sync():
        """Tarea de sincronización en background con manejo defensivo."""
        from database import SessionLocal
        async_db = SessionLocal()
        try:
            sync_agent = async_db.query(Agent).filter(Agent.id == agent_id).first()
            if not sync_agent:
                return

            count, message = await wasi_service.sync_inventory_to_agent_knowledge(
                async_db, sync_agent
            )
            sync_agent.wasi_sync_status = "completed" if count > 0 else "failed"
            sync_agent.wasi_last_sync_at = datetime.now(timezone.utc) if count > 0 else sync_agent.wasi_last_sync_at
            sync_agent.wasi_properties_count = count
            async_db.commit()
            logger.info("Sync Wasi completado: %s — %s", agent_id, message)
        except Exception as e:
            logger.error("Sync Wasi background error: %s", e, exc_info=True)
            try:
                fail_agent = async_db.query(Agent).filter(Agent.id == agent_id).first()
                if fail_agent:
                    fail_agent.wasi_sync_status = "failed"
                    async_db.commit()
            except Exception:
                pass
        finally:
            async_db.close()

    background_tasks.add_task(_do_sync)

    return {
        "status": "syncing",
        "message": (
            "Sincronización iniciada. El inventario de Wasi.co se está cargando "
            "a la base de conocimiento del agente. Consulta el estado en unos segundos."
        ),
    }


@router.post("/disconnect/{agent_id}")
async def disconnect_wasi(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Desconecta la integración Wasi del agente eliminando las credenciales almacenadas.
    No elimina el inventario ya sincronizado en el RAG.
    """
    agent = _get_agent_or_404(db, agent_id, current_user)

    agent.wasi_company_id = None
    agent.wasi_token = None
    agent.wasi_connected = False
    agent.wasi_sync_status = "idle"
    agent.wasi_last_sync_at = None
    agent.wasi_properties_count = 0
    db.commit()

    logger.info("Wasi desconectado para agente %s", agent_id)
    return {"status": "disconnected", "message": "Integración con Wasi.co desconectada."}


@router.post("/search-properties/{agent_id}")
async def search_properties_debug(
    agent_id: str,
    payload: WasiSearchRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Endpoint de debug: busca propiedades en Wasi con los filtros especificados.
    Útil para probar la búsqueda antes de que el agente de IA lo haga.
    """
    agent = _get_agent_or_404(db, agent_id, current_user)

    if not agent.wasi_connected or not agent.wasi_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wasi no está conectado en este agente.",
        )

    raw_token = _decrypt(agent.wasi_token)
    results = await wasi_service.search_wasi_properties(
        company_id=agent.wasi_company_id,
        wasi_token=raw_token,
        tipo_propiedad=payload.tipo_propiedad,
        proposito=payload.proposito,
        presupuesto_min=payload.presupuesto_min,
        presupuesto_max=payload.presupuesto_max,
        zona=payload.zona,
        max_results=payload.max_resultados,
    )

    return {
        "status": "success",
        "total_found": len(results),
        "properties": results,
    }
