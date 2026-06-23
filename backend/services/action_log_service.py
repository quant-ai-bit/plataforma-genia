"""
action_log_service: servicio de auditoría de acciones MCP para PLATAFORMA GENIA.

Permite registrar el inicio de la ejecución de una herramienta y su posterior
finalización (con éxito o error) para auditoría multi-tenant.

Feature: genia-agent-platform (Tarea 7.1)
"""

import logging
from sqlalchemy.orm import Session
from models.action_log import ActionLog

logger = logging.getLogger(__name__)

async def start(
    db: Session,
    tenant_id: str,
    tool_name: str,
    input_params: dict,
    model_provider: str | None = None,
) -> ActionLog:
    """
    Registra el inicio de una invocación de herramienta MCP.

    Args:
        db: Sesión de base de datos.
        tenant_id: ID del tenant que origina la acción.
        tool_name: Nombre de la herramienta invocada.
        input_params: Parámetros pasados a la herramienta.
        model_provider: Proveedor del modelo que originó la llamada (opcional).

    Returns:
        El registro `ActionLog` creado.
    """
    log = ActionLog(
        tenant_id=tenant_id,
        tool_name=tool_name,
        input_params=input_params,
        model_provider=model_provider,
        status="pending",
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    logger.info(
        "ActionLog iniciado: ID %s, Tenant %s, Tool %s",
        log.id,
        tenant_id,
        tool_name,
    )
    return log

async def complete(
    db: Session,
    log_id: str,
    status: str,
    result: dict | None = None,
    error: str | None = None,
) -> ActionLog | None:
    """
    Registra el resultado final de la invocación de la herramienta.

    Args:
        db: Sesión de base de datos.
        log_id: ID del ActionLog a completar.
        status: Estado final: 'success', 'failed' o 'unavailable'.
        result: Resultado de la invocación en formato diccionario (opcional).
        error: Mensaje de error si la invocación falló (opcional).

    Returns:
        El registro `ActionLog` actualizado o `None` si no se encontró.
    """
    log = db.query(ActionLog).filter(ActionLog.id == log_id).first()
    if not log:
        logger.warning("No se encontró ActionLog con ID %s para completar", log_id)
        return None

    log.status = status
    if result is not None:
        log.result = result
    if error is not None:
        log.error = error
        
    db.commit()
    db.refresh(log)
    logger.info("ActionLog completado: ID %s, Estado %s", log.id, status)
    return log
