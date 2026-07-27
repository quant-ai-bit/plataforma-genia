"""
ModelRotationService: monitoreo de uso de modelos para PLATAFORMA GENIA.

Ya no realiza rotación automática entre modelos gratuitos.
Conserva solo el tracking de consumo (tokens/peticiones) para fines
de monitoreo y facturación.
"""

import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from models.free_model_status import FreeModelStatus

logger = logging.getLogger(__name__)


class ModelRotationService:
    """Gestiona el monitoreo de uso de modelos."""

    @staticmethod
    def track_usage_and_check_limits(
        db: Session, provider: str, model: str, input_tokens: int, output_tokens: int
    ):
        """Registra el consumo diario del modelo Vertex AI."""
        model_id = "vertex:gemini-2.5-flash"
        total_tokens = input_tokens + output_tokens

        db_status = (
            db.query(FreeModelStatus).filter(FreeModelStatus.id == model_id).first()
        )
        if not db_status:
            db_status = FreeModelStatus(
                id=model_id,
                provider="vertex",
                model="gemini-2.5-flash",
                is_exhausted=False,
                tokens_used_today=0,
                requests_used_today=0,
            )
            db.add(db_status)

        db_status.tokens_used_today = (db_status.tokens_used_today or 0) + total_tokens
        db_status.requests_used_today = (db_status.requests_used_today or 0) + 1
        db_status.last_used = datetime.now(timezone.utc)

        db.commit()

    @staticmethod
    def get_free_tier_potentials(db: Session) -> dict:
        """Retorna potencial de tokens por dia para el modelo Vertex AI."""
        vertex_status = (
            db.query(FreeModelStatus)
            .filter(FreeModelStatus.id == "vertex:gemini-2.5-flash")
            .first()
        )
        tokens_used = vertex_status.tokens_used_today if vertex_status else 0
        requests_used = vertex_status.requests_used_today if vertex_status else 0

        return {
            "aggregate_potentials": {
                "daily_tokens": 1000000,
                "hourly_tokens": 1000000 // 24,
                "monthly_tokens": 1000000 * 30,
            },
            "models": [
                {
                    "provider": "vertex",
                    "model": "gemini-2.5-flash",
                    "tokens_used_today": tokens_used,
                    "requests_used_today": requests_used,
                    "is_exhausted": vertex_status.is_exhausted if vertex_status else False,
                    "cooldown_left_seconds": 0,
                    "potentials": {
                        "daily_tokens": 1000000,
                    },
                }
            ],
        }

    @staticmethod
    def reset_all_statuses(db: Session):
        """Limpia el estado de todos los modelos registrados."""
        db.query(FreeModelStatus).update({
            FreeModelStatus.is_exhausted: False,
            FreeModelStatus.exhausted_until: None,
            FreeModelStatus.exhausted_reason: None,
            FreeModelStatus.tokens_used_today: 0,
            FreeModelStatus.requests_used_today: 0,
        })
        db.commit()
        logger.info("Estados de modelos reiniciados.")
