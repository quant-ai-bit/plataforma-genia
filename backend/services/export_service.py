"""
export_service: Evidence_Export combinando Action_Log y Usage_Record.

Genera evidencia exportable (CSV o JSON) que combina los registros de
`action_log` y `agent_usages` (Usage_Record) por un rango de fechas y,
opcionalmente, por un `tenant_id`. Cada registro incluye el tenant, la marca de
tiempo, el tipo de operacion y el proveedor de modelo. Tambien produce una
consulta agregada de uso por tenant y periodo.

Reglas (Requisitos 6.2-6.5):
- El rango `[from, to]` es inclusivo (de 00:00:00 de `from` a 23:59:59 de `to`).
- Si se indica `tenant_id`, todos los registros pertenecen a ese tenant.
- Cada registro expone: tenant, timestamp, operation, model_provider.

Feature: genia-agent-platform (Tarea 10.1)
"""

import csv
import io
import logging
from datetime import datetime, time, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.action_log import ActionLog
from models.agent_usage import AgentUsage

logger = logging.getLogger(__name__)


def _parse_day(value: str, end: bool = False) -> datetime:
    """
    Convierte una fecha `YYYY-MM-DD` en datetime UTC (inicio o fin de dia).

    Args:
        value: Fecha en formato `YYYY-MM-DD`.
        end: Si True devuelve el fin del dia (23:59:59.999999); si no, el inicio.

    Returns:
        `datetime` con zona horaria UTC.

    Raises:
        ValueError: Si el formato de fecha es invalido.
    """
    day = datetime.strptime(value, "%Y-%m-%d").date()
    moment = time.max if end else time.min
    return datetime.combine(day, moment, tzinfo=timezone.utc)


def _iso(dt) -> str | None:
    """Serializa un datetime a ISO-8601, o None si es nulo."""
    return dt.isoformat() if dt is not None else None


def collect_action_logs(
    db: Session, start: datetime, end: datetime, tenant_id: str | None = None
) -> list[dict]:
    """Recupera los Action_Logs del rango (y tenant opcional) como dicts."""
    query = db.query(ActionLog).filter(
        ActionLog.created_at >= start, ActionLog.created_at <= end
    )
    if tenant_id:
        query = query.filter(ActionLog.tenant_id == tenant_id)
    rows = query.order_by(ActionLog.created_at.asc()).all()
    return [
        {
            "tenant_id": row.tenant_id,
            "timestamp": _iso(row.created_at),
            "operation": "mcp_invoke",
            "tool": row.tool_name,
            "status": row.status,
            "model_provider": row.model_provider,
        }
        for row in rows
    ]


def collect_usage_records(
    db: Session, start: datetime, end: datetime, tenant_id: str | None = None
) -> list[dict]:
    """Recupera los Usage_Records del rango (y tenant opcional) como dicts."""
    query = db.query(AgentUsage).filter(
        AgentUsage.last_used >= start, AgentUsage.last_used <= end
    )
    if tenant_id:
        query = query.filter(AgentUsage.tenant_id == tenant_id)
    rows = query.order_by(AgentUsage.last_used.asc()).all()
    return [
        {
            "tenant_id": row.tenant_id,
            "timestamp": _iso(row.last_used),
            "operation": "chat",
            "input_tokens": row.prompt_tokens,
            "output_tokens": row.completion_tokens,
            "model_provider": row.model_provider,
        }
        for row in rows
    ]


def aggregate_usage_by_tenant_period(
    db: Session, start: datetime, end: datetime, tenant_id: str | None = None
) -> list[dict]:
    """
    Agrega el uso por tenant y periodo (Requisito 6.5).

    Suma `prompt_tokens`, `completion_tokens` y `total_tokens` de los
    `agent_usages` del rango, agrupando por `tenant_id` y `period`.
    """
    query = db.query(
        AgentUsage.tenant_id.label("tenant_id"),
        AgentUsage.period.label("period"),
        func.coalesce(func.sum(AgentUsage.prompt_tokens), 0).label("input_tokens"),
        func.coalesce(func.sum(AgentUsage.completion_tokens), 0).label("output_tokens"),
        func.coalesce(func.sum(AgentUsage.total_tokens), 0).label("total_tokens"),
    ).filter(AgentUsage.last_used >= start, AgentUsage.last_used <= end)
    if tenant_id:
        query = query.filter(AgentUsage.tenant_id == tenant_id)
    rows = query.group_by(AgentUsage.tenant_id, AgentUsage.period).all()
    return [
        {
            "tenant_id": row.tenant_id,
            "period": row.period,
            "input_tokens": int(row.input_tokens or 0),
            "output_tokens": int(row.output_tokens or 0),
            "total_tokens": int(row.total_tokens or 0),
        }
        for row in rows
    ]


def export_json(
    db: Session, from_: str, to: str, tenant_id: str | None = None
) -> dict:
    """
    Construye la Evidence_Export en formato JSON para el rango indicado.

    Returns:
        Dict con `range`, `tenant_id`, `action_logs`, `usage_records` y
        `usage_aggregate` (agregado por tenant y periodo).
    """
    start = _parse_day(from_, end=False)
    end = _parse_day(to, end=True)
    return {
        "range": {"from": from_, "to": to},
        "tenant_id": tenant_id,
        "action_logs": collect_action_logs(db, start, end, tenant_id),
        "usage_records": collect_usage_records(db, start, end, tenant_id),
        "usage_aggregate": aggregate_usage_by_tenant_period(db, start, end, tenant_id),
    }


def export_csv(
    db: Session, from_: str, to: str, tenant_id: str | None = None
) -> str:
    """
    Construye la Evidence_Export en formato CSV para el rango indicado.

    Une Action_Logs y Usage_Records en filas con columnas comunes
    (`record_type`, `tenant_id`, `timestamp`, `operation`, `model_provider`) mas
    columnas especificas (`tool`, `status`, `input_tokens`, `output_tokens`).
    """
    data = export_json(db, from_, to, tenant_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "record_type",
            "tenant_id",
            "timestamp",
            "operation",
            "model_provider",
            "tool",
            "status",
            "input_tokens",
            "output_tokens",
        ]
    )
    for row in data["action_logs"]:
        writer.writerow(
            [
                "action_log",
                row["tenant_id"],
                row["timestamp"],
                row["operation"],
                row["model_provider"] or "",
                row["tool"] or "",
                row["status"] or "",
                "",
                "",
            ]
        )
    for row in data["usage_records"]:
        writer.writerow(
            [
                "usage_record",
                row["tenant_id"],
                row["timestamp"],
                row["operation"],
                row["model_provider"] or "",
                "",
                "",
                row["input_tokens"] or 0,
                row["output_tokens"] or 0,
            ]
        )
    return output.getvalue()
