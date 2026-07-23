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
        """Registra el consumo diario del modelo."""
        model_id = f"{provider}:{model}"
        total_tokens = input_tokens + output_tokens

        db_status = (
            db.query(FreeModelStatus).filter(FreeModelStatus.id == model_id).first()
        )
        if not db_status:
            db_status = FreeModelStatus(
                id=model_id,
                provider=provider,
                model=model,
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
        """Retorna potencial de tokens por dia para el modelo configurado."""
        now = datetime.now(timezone.utc)
        db_statuses = db.query(FreeModelStatus).all()
        status_map = {status.id: status for status in db_statuses}

        models_data = []
        total_daily_potential = 0

        for model_id, status in status_map.items():
            tokens_used = status.tokens_used_today or 0
            requests_used = status.requests_used_today or 0

            models_data.append({
                "provider": status.provider,
                "model": status.model,
                "tokens_used_today": tokens_used,
                "requests_used_today": requests_used,
                "potentials": {
                    "daily_tokens": 1000000,
                },
            })
            total_daily_potential += 1000000

        return {
            "aggregate_potentials": {
                "daily_tokens": total_daily_potential,
            },
            "models": models_data,
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
