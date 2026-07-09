"""
Router de Gestión de Modelos Gratuitos y Cuotas para PLATAFORMA GENIA.

Permite consultar el estado de cooldown/cobertura de los modelos gratuitos,
sus límites teóricos, el cálculo del potencial de tokens y reiniciar el estado.
"""

import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from services.model_rotation_service import ModelRotationService
from services.auth_service import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/free-models", tags=["Free Models Rotation"])


@router.get("/status")
def get_free_models_status(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Retorna la lista de todos los modelos gratuitos, sus cuotas teóricas,
    su estado de cooldown actual y el potencial acumulado de tokens consumibles
    por hora, día y mes.
    """
    try:
        data = ModelRotationService.get_free_tier_potentials(db)
        return data
    except Exception as e:
        logger.error("Error al obtener estado de modelos gratuitos: %s", str(e), exc_info=True)
        return {"error": str(e)}


@router.post("/reset", status_code=status.HTTP_200_OK)
def reset_free_models_status(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Limpia de manera forzada el estado de cooldown de todos los modelos gratuitos
    para que vuelvan a estar disponibles inmediatamente (útil para pruebas/administradores).
    """
    try:
        ModelRotationService.reset_all_statuses(db)
        return {"status": "success", "message": "Estado de modelos gratuitos restablecido exitosamente."}
    except Exception as e:
        logger.error("Error al restablecer estado de modelos gratuitos: %s", str(e), exc_info=True)
        return {"error": str(e)}
