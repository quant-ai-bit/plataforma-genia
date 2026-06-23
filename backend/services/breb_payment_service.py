"""
breb_payment_service: cobros Bre-B con verificacion por vision (Gemini).

Sustituye el billing de Stripe por un modelo de cobros mediante transferencia
Bre-B (llaves) confirmados por el Agente de Verificacion de Pagos:

- `create_checkout`: genera un `Payment` en estado `pending` con la llave Bre-B
  del comercio (`BREB_LLAVE`) y una `reference` unica. Devuelve los datos del
  cobro mas el QR (imagen base64 generada con la libreria `qrcode`, con
  degradacion a la cadena en texto plano si `qrcode` no esta instalada).
- `verify_payment`: recibe el comprobante (imagen base64), extrae sus datos con
  `vision_service` (Gemini) y los compara contra el cobro esperado. Si coincide,
  marca el `Payment` como `verified` y activa la `Subscription` del tenant por un
  mes; si no, lo marca `rejected` con el motivo. Es idempotente: un comprobante
  ya utilizado (o un `Payment` ya verificado) se rechaza con el motivo
  "comprobante ya utilizado".

Reglas de seguridad: la llave y el titular del comercio se leen exclusivamente
desde `Settings`/entorno (`breb_llave`, `breb_titular`); nunca se incrustan en
codigo. Cada verificacion se audita en `Action_Log`.

Feature: genia-agent-platform (Tareas 9.x - Cobros Bre-B)
"""

import base64
import binascii
import hashlib
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from config import settings
from models.payment import Payment
from services import action_log_service, billing_service

logger = logging.getLogger(__name__)

# Palabras que indican que la transaccion fue aprobada/exitosa.
APPROVED_HINTS = (
    "aprob",
    "exito",
    "complet",
    "pagad",
    "realizada",
    "confirmad",
    "success",
    "approved",
    "ok",
)

# Ventana de tolerancia (en dias) para considerar "reciente" la fecha del comprobante.
RECENT_WINDOW_DAYS = 3

# Periodo de la suscripcion activada por una verificacion exitosa (aproximado a 1 mes).
SUBSCRIPTION_PERIOD_DAYS = 30


# ── Utilidades de normalizacion ─────────────────────────────────────
def _now() -> datetime:
    """Marca de tiempo actual en UTC."""
    return datetime.now(timezone.utc)


def _generate_reference(tenant) -> str:
    """Genera una referencia unica para el cobro a partir del tenant y un UUID."""
    slug = getattr(tenant, "slug", None) or getattr(tenant, "id", "tenant")
    stamp = _now().strftime("%Y%m%d%H%M%S")
    return f"{slug}-{stamp}-{uuid.uuid4().hex[:8]}"


def _qr_payload(llave: str, amount: int, currency: str, reference: str) -> str:
    """
    Construye la cadena que codifica el QR del cobro.

    Formato compacto y documentado que el QR codifica:
        ``BREB|<llave>|<monto>|<referencia>``
    donde `monto` esta expresado en centavos de la moneda indicada. El parametro
    `currency` se conserva por compatibilidad de firma (no se incrusta en la
    cadena, que asume COP).
    """
    return f"BREB|{llave}|{amount}|{reference}"


def _generate_qr_base64(payload: str) -> str:
    """
    Genera el QR del cobro como data URL PNG en base64 a partir de `payload`.

    Usa la libreria `qrcode` (con Pillow) si esta instalada. Si no esta
    disponible en el entorno, degrada con elegancia devolviendo la propia cadena
    `payload` para que el cliente pueda generar el QR por su cuenta, sin fallar.

    Returns:
        Data URL ``data:image/png;base64,<...>`` con la imagen del QR, o la
        cadena `payload` en texto plano si `qrcode` no esta disponible.
    """
    try:
        import io

        import qrcode  # type: ignore

        img = qrcode.make(payload)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception as exc:  # noqa: BLE001 - degradacion si falta `qrcode`/PIL
        logger.warning("No se pudo generar la imagen QR (qrcode no disponible?): %s", exc)
        return payload


def _decode_image(image_base64: str) -> tuple[bytes, str]:
    """
    Decodifica una imagen en base64 (admite data URLs) y deduce su mime type.

    Returns:
        Una tupla (bytes_de_imagen, mime_type).

    Raises:
        HTTPException: 422 si el base64 es invalido o esta vacio.
    """
    if not image_base64 or not isinstance(image_base64, str):
        raise HTTPException(status_code=422, detail="Comprobante ilegible: imagen vacia")

    mime_type = "image/jpeg"
    data = image_base64.strip()
    if data.startswith("data:"):
        header, _, payload = data.partition(",")
        match = re.match(r"data:([^;]+)", header)
        if match:
            mime_type = match.group(1)
        data = payload

    try:
        image_bytes = base64.b64decode(data, validate=False)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=422, detail="Comprobante ilegible: base64 invalido"
        ) from exc

    if not image_bytes:
        raise HTTPException(status_code=422, detail="Comprobante ilegible: imagen vacia")
    return image_bytes, mime_type


def _parse_pesos(raw) -> float | None:
    """Convierte un importe en texto/numero a pesos (float), o None si no se puede."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = re.sub(r"[^0-9.,]", "", str(raw))
    if not s:
        return None
    if "," in s and "." in s:
        # El ultimo separador es el decimal.
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[-1]) == 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "." in s:
        parts = s.split(".")
        if not (len(parts) == 2 and len(parts[-1]) == 2):
            s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def _to_centavos(raw) -> int | None:
    """Normaliza un importe (en pesos) a centavos enteros."""
    pesos = _parse_pesos(raw)
    if pesos is None:
        return None
    return int(round(pesos * 100))


def _norm_key(value) -> str:
    """Normaliza una llave/cuenta para comparacion laxa (minusculas, sin separadores)."""
    return re.sub(r"[^a-z0-9@.]", "", str(value or "").lower())


def _is_approved(estado) -> bool:
    """Indica si el estado textual del comprobante corresponde a una operacion aprobada."""
    text = str(estado or "").lower()
    if not text:
        return False
    if any(bad in text for bad in ("rechaz", "fallid", "pendiente", "declin", "error")):
        return False
    return any(hint in text for hint in APPROVED_HINTS)


def _is_recent(fecha, days: int = RECENT_WINDOW_DAYS) -> bool:
    """
    Indica si la fecha del comprobante es reciente (dentro de la ventana).

    Si la fecha no puede interpretarse, se concede el beneficio de la duda
    (devuelve True) para no rechazar comprobantes validos por formatos OCR raros.
    """
    if not fecha:
        return True
    text = str(fecha).strip()
    formats = (
        "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
        "%d/%m/%Y", "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y", "%d-%m-%Y %H:%M", "%m/%d/%Y",
    )
    parsed = None
    for fmt in formats:
        try:
            parsed = datetime.strptime(text[: len(fmt) + 4], fmt)
            break
        except ValueError:
            continue
    if parsed is None:
        # Intento adicional: fecha embebida con regex AAAA-MM-DD o DD/MM/AAAA.
        m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
        if m:
            try:
                parsed = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                parsed = None
        if parsed is None:
            m = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", text)
            if m:
                try:
                    parsed = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                except ValueError:
                    parsed = None
    if parsed is None:
        return True
    now = datetime.now()
    delta = now - parsed
    return timedelta(days=-1) <= delta <= timedelta(days=days)


# ── Operaciones de cobro ────────────────────────────────────────────
def create_checkout(
    db: Session,
    tenant,
    amount: int | None = None,
    reference: str | None = None,
) -> dict:
    """
    Crea un cobro Bre-B en estado `pending` para el tenant.

    Args:
        db: Sesion de base de datos.
        tenant: Tenant propietario del cobro (expone `.id` y opcionalmente `.slug`).
        amount: Monto esperado en centavos de COP; por defecto `subscription_amount_cop`.
        reference: Referencia del cobro; si no se indica, se genera una unica.

    Returns:
        Dict con `reference`, `llave`, `titular`, `amount`, `currency`, `qr`
        (imagen base64 del QR) y `qr_payload` (cadena codificada en el QR).

    Raises:
        HTTPException: 409 si la `reference` indicada ya existe para el tenant.
        RuntimeError: si `BREB_LLAVE` no esta configurada en el entorno.
    """
    llave = settings.breb_llave
    if not llave:
        raise RuntimeError("BREB_LLAVE no esta configurada en el entorno.")
    titular = settings.breb_titular
    currency = "COP"
    expected_amount = int(amount) if amount is not None else int(settings.subscription_amount_cop)
    reference = reference or _generate_reference(tenant)

    existing = (
        db.query(Payment)
        .filter(Payment.tenant_id == tenant.id, Payment.reference == reference)
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=409, detail="Ya existe un cobro con esa referencia"
        )

    payment = Payment(
        tenant_id=tenant.id,
        reference=reference,
        expected_amount=expected_amount,
        currency=currency,
        llave_destino=llave,
        status="pending",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    logger.info(
        "Checkout Bre-B creado: tenant=%s reference=%s amount=%s",
        tenant.id,
        reference,
        expected_amount,
    )

    return {
        "reference": reference,
        "llave": llave,
        "titular": titular,
        "amount": expected_amount,
        "currency": currency,
        "qr_payload": _qr_payload(llave, expected_amount, currency, reference),
        "qr": _generate_qr_base64(
            _qr_payload(llave, expected_amount, currency, reference)
        ),
    }


async def verify_payment(
    db: Session,
    tenant,
    reference: str,
    image_base64: str,
) -> dict:
    """
    Verifica un comprobante Bre-B contra el cobro esperado del tenant.

    Busca el `Payment` por (tenant, reference) (404 si no existe), extrae los datos
    del comprobante con `vision_service` (Gemini) y los compara con lo esperado
    (monto, llave destino, estado aprobado y fecha reciente). Aplica idempotencia:
    si el `Payment` ya esta verificado o el comprobante ya fue usado, responde
    `rejected` con motivo "comprobante ya utilizado". Si coincide, marca `verified`,
    guarda los datos extraidos y activa la `Subscription` del tenant por un mes; si
    no, marca `rejected` con el motivo. Cada verificacion se registra en `Action_Log`.

    Args:
        db: Sesion de base de datos.
        tenant: Tenant autenticado.
        reference: Referencia del cobro a verificar.
        image_base64: Imagen del comprobante en base64 (admite data URL).

    Returns:
        Dict con `status` ('verified' | 'rejected'), `reason` (str | None) y
        `extracted` (datos del comprobante o None).

    Raises:
        HTTPException: 404 si el cobro no existe; 422 si el comprobante es ilegible.
    """
    # Importacion diferida para no acoplar el arranque a la disponibilidad de Gemini.
    from services import vision_service

    payment = (
        db.query(Payment)
        .filter(Payment.tenant_id == tenant.id, Payment.reference == reference)
        .first()
    )
    if payment is None:
        raise HTTPException(status_code=404, detail="Cobro no encontrado")

    log = await action_log_service.start(
        db,
        tenant_id=tenant.id,
        tool_name="payment.verify",
        input_params={"reference": reference},
        model_provider="gemini",
    )

    # Idempotencia: un Payment ya verificado no se vuelve a acreditar.
    if payment.status == "verified":
        await action_log_service.complete(
            db, log.id, status="failed", result={"reason": "comprobante ya utilizado"}
        )
        return {
            "status": "rejected",
            "reason": "comprobante ya utilizado",
            "extracted": payment.extracted,
        }

    # Decodificar imagen (422 si es ilegible) y calcular su huella para anti-reuso.
    image_bytes, mime_type = _decode_image(image_base64)
    comprobante_hash = hashlib.sha256(image_bytes).hexdigest()

    used = (
        db.query(Payment)
        .filter(
            Payment.comprobante_ref == comprobante_hash,
            Payment.status == "verified",
        )
        .first()
    )
    if used is not None:
        payment.status = "rejected"
        payment.reject_reason = "comprobante ya utilizado"
        await action_log_service.complete(
            db, log.id, status="failed", result={"reason": "comprobante ya utilizado"}
        )
        return {
            "status": "rejected",
            "reason": "comprobante ya utilizado",
            "extracted": None,
        }

    # Si el servicio de vision no tiene credenciales (Gemini/Vertex), no es
    # posible verificar automaticamente: se deja el cobro en revision manual
    # ('pending_manual_review') en vez de fallar, segun el alcance acordado.
    has_vision_creds = bool(
        getattr(settings, "gemini_api_key", "")
        or getattr(settings, "google_cloud_project", "")
    )
    if not has_vision_creds:
        payment.status = "pending_manual_review"
        await action_log_service.complete(
            db,
            log.id,
            status="pending_manual_review",
            result={"reason": "servicio de vision sin credenciales"},
        )
        logger.warning(
            "Verificacion Bre-B en revision manual (sin credenciales de vision): "
            "tenant=%s ref=%s",
            tenant.id,
            reference,
        )
        return {
            "status": "pending_manual_review",
            "reason": "servicio de vision sin credenciales; pendiente de revision manual",
            "extracted": None,
        }

    # Extraccion por vision. Vacio => ilegible => 422.
    try:
        extracted = vision_service.extract_payment_receipt(image_bytes, mime_type)
    except ValueError:
        # Configuracion del proveedor incompleta: revision manual en vez de error.
        payment.status = "pending_manual_review"
        await action_log_service.complete(
            db,
            log.id,
            status="pending_manual_review",
            result={"reason": "servicio de vision no disponible"},
        )
        return {
            "status": "pending_manual_review",
            "reason": "servicio de vision no disponible; pendiente de revision manual",
            "extracted": None,
        }
    if not extracted:
        await action_log_service.complete(
            db, log.id, status="failed", error="comprobante ilegible"
        )
        raise HTTPException(
            status_code=422, detail="Comprobante ilegible o sin datos extraibles"
        )

    # Validaciones contra lo esperado.
    reasons: list[str] = []

    extracted_centavos = _to_centavos(extracted.get("monto"))
    if extracted_centavos is None or extracted_centavos != payment.expected_amount:
        reasons.append(
            f"monto no coincide (esperado {payment.expected_amount} centavos, "
            f"detectado {extracted.get('monto')!r})"
        )

    destino = extracted.get("llave_o_cuenta_destino")
    expected_llave = _norm_key(payment.llave_destino)
    if not expected_llave or expected_llave not in _norm_key(destino):
        reasons.append("la llave/cuenta destino no coincide con el comercio")

    if not _is_approved(extracted.get("estado")):
        reasons.append("la transaccion no figura como aprobada")

    if not _is_recent(extracted.get("fecha")):
        reasons.append("la fecha del comprobante no es reciente")

    if reasons:
        reason = "; ".join(reasons)
        payment.status = "rejected"
        payment.reject_reason = reason
        payment.extracted = extracted
        await action_log_service.complete(
            db, log.id, status="failed", result={"reason": reason}
        )
        logger.info("Verificacion Bre-B rechazada: tenant=%s ref=%s motivo=%s", tenant.id, reference, reason)
        return {"status": "rejected", "reason": reason, "extracted": extracted}

    # Coincide: acreditar el cobro y activar la suscripcion por un mes.
    now = _now()
    payment.status = "verified"
    payment.verified_at = now
    payment.extracted = extracted
    payment.comprobante_ref = comprobante_hash

    billing_service.upsert_subscription(
        db,
        tenant.id,
        status="activa",
        current_period_start=now,
        current_period_end=now + timedelta(days=SUBSCRIPTION_PERIOD_DAYS),
    )

    await action_log_service.complete(
        db, log.id, status="success", result={"reference": reference, "status": "verified"}
    )
    logger.info("Verificacion Bre-B exitosa: tenant=%s ref=%s", tenant.id, reference)
    return {"status": "verified", "reason": None, "extracted": extracted}