"""
ModelRotationService: servicio para rotar modelos gratuitos y calcular cuotas/potenciales
para PLATAFORMA GENIA.
"""

import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from models.free_model_status import FreeModelStatus

logger = logging.getLogger(__name__)

# Catálogo prioritario de modelos gratuitos y de alta disponibilidad
FREE_MODELS = [
    {"provider": "gemini", "model": "gemini-2.0-flash", "priority": 1},
    {"provider": "groq", "model": "llama-3.3-70b-versatile", "priority": 2},
    {"provider": "groq", "model": "llama-3.1-8b-instant", "priority": 3},
    {"provider": "openrouter", "model": "deepseek/deepseek-chat", "priority": 4},
    {"provider": "openrouter", "model": "openai/gpt-4o-mini", "priority": 5},
]

# Cuotas teóricas oficiales y estimadas de los modelos gratuitos
FREE_MODELS_QUOTAS = {
    "gemini-2.0-flash": {
        "rpm": 10,
        "tpm": 1000000,
        "rpd": 1500,
        "tpd": None,
        "reset_time_description": "RPM y TPM se recargan cada minuto. RPD se recarga diariamente a las 08:00 UTC.",
    },
    "gemini-2.5-flash": {
        "rpm": 15,
        "tpm": 1000000,
        "rpd": 1500,
        "tpd": None,
        "reset_time_description": "RPM y TPM se recargan cada minuto. RPD se recarga diariamente a las 08:00 UTC.",
    },
    "llama-3.3-70b-versatile": {
        "rpm": 30,
        "tpm": 6000,
        "rpd": 14400,
        "tpd": None,
        "reset_time_description": "Límites por minuto (RPM/TPM) móviles. Límites diarios (RPD) se recargan cada 24 horas.",
    },
    "llama-3.1-8b-instant": {
        "rpm": 30,
        "tpm": 30000,
        "rpd": 14400,
        "tpd": None,
        "reset_time_description": "Límites por minuto (RPM/TPM) móviles. Límites diarios (RPD) se recargan cada 24 horas.",
    },
    "google/gemini-2.5-flash": {
        "rpm": 10,
        "tpm": 100000,
        "rpd": 2000,
        "tpd": None,
        "reset_time_description": "Límites por minuto móviles. Límites diarios se recargan a las 00:00 UTC.",
    },
    "deepseek/deepseek-chat": {
        "rpm": 10,
        "tpm": 100000,
        "rpd": 2000,
        "tpd": None,
        "reset_time_description": "Límites diarios se recargan a las 00:00 UTC.",
    },
    "openai/gpt-4o-mini": {
        "rpm": 10,
        "tpm": 100000,
        "rpd": 2000,
        "tpd": None,
        "reset_time_description": "Límites diarios se recargan a las 00:00 UTC.",
    },
}


class ModelRotationService:
    """Gestiona la selección, inhabilitación temporal y cálculo de potenciales de los modelos gratuitos."""

    @staticmethod
    def get_next_available_free_model(
        db: Session,
        current_provider: str | None = None,
        current_model: str | None = None,
    ) -> dict:
        """
        Retorna el mejor modelo gratuito disponible que no esté en cooldown.
        Evita retornar el modelo actual que falló a menos que no haya otro disponible.
        """
        now = datetime.now(timezone.utc)

        # Cargar los estados de agotamiento actuales desde base de datos
        db_statuses = db.query(FreeModelStatus).all()
        status_map = {status.id: status for status in db_statuses}

        available_candidates = []
        for m in FREE_MODELS:
            model_id = f"{m['provider']}:{m['model']}"
            db_status = status_map.get(model_id)

            is_exhausted = False
            if db_status:
                # Si el cooldown ya pasó, se considera disponible
                if db_status.is_exhausted:
                    # Normalizar para comparar naive vs aware
                    exhausted_until = db_status.exhausted_until
                    compare_now = now
                    if exhausted_until is not None:
                        if (
                            exhausted_until.tzinfo is None
                            and compare_now.tzinfo is not None
                        ):
                            compare_now = compare_now.replace(tzinfo=None)
                        elif (
                            exhausted_until.tzinfo is not None
                            and compare_now.tzinfo is None
                        ):
                            compare_now = compare_now.replace(tzinfo=timezone.utc)

                        if compare_now >= exhausted_until:
                            # Restablecer estado agotado automáticamente en la DB
                            db_status.is_exhausted = False
                            db_status.exhausted_until = None
                            db_status.exhausted_reason = None
                            db.commit()
                        else:
                            is_exhausted = True
                    else:
                        is_exhausted = True

            if not is_exhausted:
                # No preferir el modelo que actualmente falló
                is_current = (
                    m["provider"] == current_provider and m["model"] == current_model
                )
                penalty = 100 if is_current else 0
                available_candidates.append(
                    {
                        "provider": m["provider"],
                        "model": m["model"],
                        "priority": m["priority"] + penalty,
                    }
                )

        if not available_candidates:
            logger.warning(
                "Todos los modelos gratuitos están en cooldown. Utilizando el de prioridad superior."
            )
            # Si todos están agotados, retornar el de mayor prioridad por defecto (primer elemento)
            return FREE_MODELS[0]

        # Ordenar por prioridad final (menor número es mayor prioridad)
        available_candidates.sort(key=lambda x: x["priority"])
        return available_candidates[0]

    @staticmethod
    def mark_model_exhausted(
        db: Session,
        provider: str,
        model: str,
        reason: str,
        cooldown_seconds: int | None = None,
    ) -> datetime:
        """
        Marca un modelo como agotado en la base de datos y define su hora de reactivación (cooldown).
        """
        now = datetime.now(timezone.utc)
        model_id = f"{provider}:{model}"

        # Determinar cooldown si no se provee
        if not cooldown_seconds:
            reason_lower = reason.lower() if reason else ""
            if (
                "decommissioned" in reason_lower
                or "not found" in reason_lower
                or "not supported" in reason_lower
                or "400" in reason_lower
            ):
                # Bloqueo por 30 días para modelos descontinuados o inexistentes
                cooldown_seconds = 30 * 24 * 3600
            elif (
                "429" in reason
                or "rate_limit" in reason_lower
                or "limit reached" in reason_lower
                or "too many requests" in reason_lower
            ):
                cooldown_seconds = 60
            else:
                # Si es por cuota agotada (quota exceeded / 402 OpenRouter), se asume cuota diaria y se bloquea por 12 horas
                cooldown_seconds = 12 * 3600

        reactivation_time = now + timedelta(seconds=cooldown_seconds)

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
        else:
            if db_status.is_exhausted is None:
                db_status.is_exhausted = False
            if db_status.tokens_used_today is None:
                db_status.tokens_used_today = 0
            if db_status.requests_used_today is None:
                db_status.requests_used_today = 0

        db_status.is_exhausted = True
        db_status.exhausted_until = reactivation_time
        db_status.exhausted_reason = reason[:255] if reason else None
        db.commit()

        logger.info(
            "Modelo '%s' marcado como agotado. Motivo: %s. Reactivación a las %s UTC",
            model_id,
            reason,
            reactivation_time.isoformat(),
        )
        return reactivation_time

    @staticmethod
    def track_usage_and_check_limits(
        db: Session, provider: str, model: str, input_tokens: int, output_tokens: int
    ):
        """
        Registra el consumo diario de un modelo y valida proactivamente si supera sus cuotas estimadas.
        """
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
        else:
            if db_status.is_exhausted is None:
                db_status.is_exhausted = False
            if db_status.tokens_used_today is None:
                db_status.tokens_used_today = 0
            if db_status.requests_used_today is None:
                db_status.requests_used_today = 0

        db_status.tokens_used_today += total_tokens
        db_status.requests_used_today += 1
        db_status.last_used = datetime.now(timezone.utc)

        # Validar límites diarios si están definidos
        quota = FREE_MODELS_QUOTAS.get(model)
        if quota:
            rpd_limit = quota.get("rpd")
            if rpd_limit and db_status.requests_used_today >= rpd_limit:
                db_status.is_exhausted = True
                # Cooldown hasta el final del día (siguiente 08:00 UTC para Gemini o 00:00 UTC para OpenRouter)
                now = datetime.now(timezone.utc)
                tomorrow = (now + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                db_status.exhausted_until = tomorrow
                db_status.exhausted_reason = (
                    "Supera límite proactivo diario de peticiones (RPD)"
                )
                logger.warning(
                    "Modelo '%s' superó proactivamente su cuota diaria. Cooldown hasta %s",
                    model_id,
                    tomorrow.isoformat(),
                )

        db.commit()

    @staticmethod
    def reset_all_statuses(db: Session):
        """
        Limpia el estado de agotamiento de todos los modelos registrados.
        """
        db.query(FreeModelStatus).update(
            {
                FreeModelStatus.is_exhausted: False,
                FreeModelStatus.exhausted_until: None,
                FreeModelStatus.exhausted_reason: None,
                FreeModelStatus.tokens_used_today: 0,
                FreeModelStatus.requests_used_today: 0,
            }
        )
        db.commit()
        logger.info("Restablecido el estado de todos los modelos gratuitos.")

    @staticmethod
    def get_free_tier_potentials(db: Session) -> dict:
        """
        Calcula las cuotas y los potenciales de tokens consumibles por hora, día y mes
        para cada modelo individualmente y en total.
        """
        now = datetime.now(timezone.utc)
        db_statuses = db.query(FreeModelStatus).all()
        status_map = {status.id: status for status in db_statuses}

        models_data = []
        total_hourly_potential = 0
        total_daily_potential = 0
        total_monthly_potential = 0

        # Suposición: 1 request promedio gasta unos 2,500 tokens (entrada + salida)
        avg_tokens_per_req = 2500

        for m in FREE_MODELS:
            model = m["model"]
            provider = m["provider"]
            model_id = f"{provider}:{model}"

            quota = FREE_MODELS_QUOTAS.get(
                model,
                {
                    "rpm": 10,
                    "tpm": 50000,
                    "rpd": 1000,
                    "tpd": None,
                    "reset_time_description": "Desconocido",
                },
            )

            # Calcular potenciales de tokens por periodo
            # 1. Diario: limitado por RPD * tokens_por_req
            rpd = quota.get("rpd") or 1000
            daily_tokens = rpd * avg_tokens_per_req

            # 2. Horario: limitado por TPM * 60, pero no puede exceder el diario / 24
            tpm = quota.get("tpm") or (quota.get("rpm", 10) * avg_tokens_per_req)
            hourly_tokens = min(tpm * 60, daily_tokens / 24)

            # 3. Mensual: diario * 30
            monthly_tokens = daily_tokens * 30

            # Acumular totales
            total_hourly_potential += hourly_tokens
            total_daily_potential += daily_tokens
            total_monthly_potential += monthly_tokens

            # Estado actual en DB
            db_status = status_map.get(model_id)
            is_exhausted = False
            cooldown_left_seconds = 0
            reason = None
            tokens_used = 0
            requests_used = 0

            if db_status:
                tokens_used = db_status.tokens_used_today
                requests_used = db_status.requests_used_today
                if db_status.is_exhausted:
                    exhausted_until = db_status.exhausted_until
                    compare_now = now
                    if exhausted_until is not None:
                        if (
                            exhausted_until.tzinfo is None
                            and compare_now.tzinfo is not None
                        ):
                            compare_now = compare_now.replace(tzinfo=None)
                        elif (
                            exhausted_until.tzinfo is not None
                            and compare_now.tzinfo is None
                        ):
                            compare_now = compare_now.replace(tzinfo=timezone.utc)

                        if exhausted_until > compare_now:
                            is_exhausted = True
                            cooldown_left_seconds = int(
                                (exhausted_until - compare_now).total_seconds()
                            )
                            reason = db_status.exhausted_reason

            models_data.append(
                {
                    "provider": provider,
                    "model": model,
                    "priority": m["priority"],
                    "is_exhausted": is_exhausted,
                    "cooldown_left_seconds": cooldown_left_seconds,
                    "reason": reason,
                    "tokens_used_today": tokens_used,
                    "requests_used_today": requests_used,
                    "limits": {
                        "rpm": quota.get("rpm"),
                        "tpm": quota.get("tpm"),
                        "rpd": quota.get("rpd"),
                    },
                    "potentials": {
                        "hourly_tokens": int(hourly_tokens),
                        "daily_tokens": int(daily_tokens),
                        "monthly_tokens": int(monthly_tokens),
                    },
                    "reset_time_description": quota.get("reset_time_description"),
                }
            )

        return {
            "aggregate_potentials": {
                "hourly_tokens": int(total_hourly_potential),
                "daily_tokens": int(total_daily_potential),
                "monthly_tokens": int(total_monthly_potential),
            },
            "models": models_data,
        }
