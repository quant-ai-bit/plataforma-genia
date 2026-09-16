"""
Servicio de Integración con Wasi.co para PLATAFORMA GENIA.

Proporciona funciones para:
  - Validar credenciales de la API de Wasi (id_company + wasi_token).
  - Buscar propiedades en tiempo real con filtros del cliente (tipo, propósito,
    presupuesto, zona) y retornar máximo 3 resultados con links directos.
  - Sincronizar el inventario activo al RAG del agente (base de conocimiento vectorial)
    para funcionamiento defensivo sin conexión.
  - Crear clientes (leads) en Wasi.co CRM.

API Reference: https://api.wasi.co/docs/guide/getting-started.html
Autenticación: GET/POST con parámetros id_company + wasi_token.
"""

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

WASI_BASE_URL = "https://api.wasi.co/v1"
WASI_TIMEOUT = 12.0  # segundos — defensivo


# ── Tipos de propiedad Wasi (id_property_type → nombre) ─────────────
# Ref: https://api.wasi.co/docs/guide/fields/property-types.html
WASI_PROPERTY_TYPES: dict[str, int] = {
    "Casa": 1,
    "Apartamento": 2,
    "Local Comercial": 3,
    "Oficina": 4,
    "Bodega": 5,
    "Lote / Terreno": 7,
    "Casa Campestre": 13,
    "Apartaestudio": 14,
    "Finca": 15,
    "Parqueadero": 16,
    "Consultorio": 23,
    "Otro": 0,
}


def _build_params(company_id: str, token: str, extra: dict | None = None) -> dict:
    """Construye los parámetros base de autenticación para cualquier llamada."""
    params: dict = {"id_company": company_id, "wasi_token": token}
    if extra:
        params.update(extra)
    return params


def _format_price(value: str | int | float) -> str:
    """Formatea un precio numérico en formato COP legible."""
    try:
        return f"${int(float(str(value))):,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(value)


def _format_property(prop: dict) -> dict:
    """
    Convierte un registro de propiedad de la API Wasi en un dict limpio y
    legible para el agente de IA.
    """
    tipo_raw = prop.get("id_property_type", 0)
    tipo_label = next(
        (k for k, v in WASI_PROPERTY_TYPES.items() if v == int(tipo_raw or 0)),
        "Propiedad",
    )

    sale_price = prop.get("sale_price", "0") or "0"
    rent_price = prop.get("rent_price", "0") or "0"

    for_sale = str(prop.get("for_sale", "false")).lower() == "true"
    for_rent = str(prop.get("for_rent", "false")).lower() == "true"

    precio_str = ""
    if for_sale and float(str(sale_price).replace(",", ".") or "0") > 0:
        precio_str = f"Venta: {_format_price(sale_price)} COP"
    if for_rent and float(str(rent_price).replace(",", ".") or "0") > 0:
        arrendamiento = f"Arriendo: {_format_price(rent_price)} COP/mes"
        precio_str = f"{precio_str} | {arrendamiento}" if precio_str else arrendamiento

    city = prop.get("city_label", "")
    region = prop.get("region_label", "")
    zone = prop.get("zone_label", "")
    location_parts = [p for p in [zone, city, region] if p]
    location_str = ", ".join(location_parts) if location_parts else "Colombia"

    link = prop.get("link", "")
    property_id = prop.get("id_property", "")
    main_img_url = ""
    main_img = prop.get("main_image")
    if isinstance(main_img, dict):
        main_img_url = main_img.get("url_big", "") or main_img.get("url", "") or ""

    return {
        "id": property_id,
        "tipo": tipo_label,
        "titulo": prop.get("title", f"Propiedad #{property_id}"),
        "precio": precio_str or "Precio a consultar",
        "area": f"{prop.get('area', 'N/A')} m²",
        "habitaciones": prop.get("bedrooms", "N/A"),
        "banos": prop.get("bathrooms", "N/A"),
        "garajes": prop.get("garages", "0"),
        "ubicacion": location_str,
        "descripcion": (prop.get("observations", "") or "")[:300],
        "link": link,
        "imagen": main_img_url,
        "para_venta": for_sale,
        "para_arriendo": for_rent,
        "disponibilidad": prop.get("availability_label", "Disponible"),
    }


def _property_to_text(prop_fmt: dict) -> str:
    """Convierte un dict formateado de propiedad en texto descriptivo para RAG."""
    lines = [
        f"TIPO: {prop_fmt['tipo']}",
        f"TÍTULO: {prop_fmt['titulo']}",
        f"PRECIO: {prop_fmt['precio']}",
        f"ÁREA: {prop_fmt['area']}",
        f"HABITACIONES: {prop_fmt['habitaciones']}  |  BAÑOS: {prop_fmt['banos']}  |  GARAJES: {prop_fmt['garajes']}",
        f"UBICACIÓN: {prop_fmt['ubicacion']}",
        f"DISPONIBILIDAD: {prop_fmt['disponibilidad']}",
    ]
    if prop_fmt["descripcion"]:
        lines.append(f"DESCRIPCIÓN: {prop_fmt['descripcion']}")
    if prop_fmt["link"]:
        lines.append(f"ENLACE: {prop_fmt['link']}")
    return "\n".join(lines)


# ── Funciones principales ─────────────────────────────────────────────


async def validate_credentials(company_id: str, wasi_token: str) -> bool:
    """
    Verifica que las credenciales de Wasi son válidas haciendo una petición
    liviana al endpoint de países.

    Returns:
        True si las credenciales son válidas, False en caso contrario.
    """
    try:
        async with httpx.AsyncClient(timeout=WASI_TIMEOUT) as client:
            resp = await client.get(
                f"{WASI_BASE_URL}/location/all-countries",
                params=_build_params(company_id, wasi_token),
            )
            data = resp.json()
            return data.get("status") == "success"
    except Exception as e:
        logger.warning("Wasi validate_credentials falló: %s", e)
        return False


async def fetch_active_properties(
    company_id: str,
    wasi_token: str,
    take: int = 100,
) -> list[dict]:
    """
    Obtiene todas las propiedades activas (disponibles) de la inmobiliaria.

    Args:
        company_id: ID de empresa Wasi.
        wasi_token: Token de acceso Wasi.
        take: Máximo de propiedades a traer (paginación).

    Returns:
        Lista de propiedades formateadas.
    """
    properties: list[dict] = []
    try:
        params = _build_params(company_id, wasi_token, {
            "id_availability": 1,  # 1 = Disponible
            "take": take,
            "short": "false",
        })
        async with httpx.AsyncClient(timeout=WASI_TIMEOUT) as client:
            resp = await client.get(
                f"{WASI_BASE_URL}/property/search",
                params=params,
            )
            data = resp.json()
            if data.get("status") != "success":
                logger.warning("Wasi fetch_active_properties: status=%s", data.get("status"))
                return []

            for key, value in data.items():
                if key in ("status", "total"):
                    continue
                if isinstance(value, dict) and "id_property" in value:
                    try:
                        properties.append(_format_property(value))
                    except Exception as e:
                        logger.debug("Error formateando propiedad %s: %s", key, e)

        logger.info("Wasi: %d propiedades obtenidas para company_id=%s", len(properties), company_id)
    except Exception as e:
        logger.error("Wasi fetch_active_properties error: %s", e)

    return properties


async def search_wasi_properties(
    company_id: str,
    wasi_token: str,
    tipo_propiedad: str | None = None,
    proposito: str | None = None,
    presupuesto_min: int | None = None,
    presupuesto_max: int | None = None,
    zona: str | None = None,
    max_results: int = 3,
) -> list[dict]:
    """
    Busca propiedades en Wasi con filtros específicos del cliente y retorna
    máximo `max_results` opciones ordenadas por relevancia.

    Args:
        company_id: ID empresa Wasi.
        wasi_token: Token de acceso Wasi.
        tipo_propiedad: Ej. "Apartamento", "Casa", "Lote / Terreno".
        proposito: "Vivir" o "Inversión" (determina if sale vs rent).
        presupuesto_min: Presupuesto mínimo en COP.
        presupuesto_max: Presupuesto máximo en COP.
        zona: Nombre de zona/barrio/ciudad de interés.
        max_results: Máximo de resultados a retornar (default 3).

    Returns:
        Lista de hasta `max_results` propiedades formateadas con link.
    """
    params: dict[str, Any] = _build_params(company_id, wasi_token, {
        "id_availability": 1,
        "take": 50,
        "short": "false",
    })

    # Filtro por tipo de propiedad
    if tipo_propiedad:
        prop_type_id = WASI_PROPERTY_TYPES.get(tipo_propiedad)
        if prop_type_id:
            params["id_property_type"] = prop_type_id

    # Filtro por propósito (venta vs arriendo)
    if proposito:
        proposito_lower = proposito.lower()
        if "inver" in proposito_lower or "arrend" in proposito_lower or "renta" in proposito_lower:
            params["for_rent"] = "true"
        else:
            params["for_sale"] = "true"

    # Filtro por precio máximo
    if presupuesto_max:
        params["price_to"] = presupuesto_max
    if presupuesto_min:
        params["price_from"] = presupuesto_min

    results: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=WASI_TIMEOUT) as client:
            resp = await client.get(
                f"{WASI_BASE_URL}/property/search",
                params=params,
            )
            data = resp.json()
            if data.get("status") != "success":
                logger.warning("Wasi search: status=%s", data.get("status"))
                return []

            for key, value in data.items():
                if key in ("status", "total"):
                    continue
                if isinstance(value, dict) and "id_property" in value:
                    try:
                        fmt = _format_property(value)
                        # Filtro adicional por zona si se especificó (búsqueda en texto)
                        if zona:
                            zona_lower = zona.lower()
                            ubicacion_lower = fmt["ubicacion"].lower()
                            titulo_lower = fmt["titulo"].lower()
                            if zona_lower not in ubicacion_lower and zona_lower not in titulo_lower:
                                continue
                        results.append(fmt)
                        if len(results) >= max_results:
                            break
                    except Exception as e:
                        logger.debug("Error en search_wasi_properties item %s: %s", key, e)

    except Exception as e:
        logger.error("Wasi search_wasi_properties error: %s", e)

    logger.info(
        "Wasi search: %d resultados (tipo=%s, propósito=%s, max_presup=%s, zona=%s)",
        len(results), tipo_propiedad, proposito, presupuesto_max, zona,
    )
    return results[:max_results]


async def sync_inventory_to_agent_knowledge(db, agent) -> tuple[int, str]:
    """
    Sincroniza el inventario activo de Wasi al RAG del agente.

    Pasos:
    1. Obtiene propiedades desde Wasi API.
    2. Elimina documentos previos de Wasi en la base de conocimiento.
    3. Crea un único documento consolidado con todo el inventario.
    4. Lo indexa en la base vectorial del agente.

    Args:
        db: Sesión SQLAlchemy.
        agent: Instancia del modelo Agent.

    Returns:
        Tupla (cantidad_propiedades, mensaje_estado).
    """
    from services.encryption_service import decrypt
    from services.knowledge_service import index_document
    from models.knowledge import KnowledgeDocument

    try:
        wasi_token_raw = decrypt(agent.wasi_token) if agent.wasi_token else None
        if not wasi_token_raw or not agent.wasi_company_id:
            return 0, "Credenciales de Wasi no configuradas."

        properties = await fetch_active_properties(agent.wasi_company_id, wasi_token_raw)
        if not properties:
            return 0, "No se encontraron propiedades disponibles en Wasi."

        # Eliminar documentos previos del inventario Wasi
        deleted = (
            db.query(KnowledgeDocument)
            .filter(
                KnowledgeDocument.agent_id == agent.id,
                KnowledgeDocument.title.like("INVENTARIO_WASI_%"),
            )
            .all()
        )
        for doc in deleted:
            from services.knowledge_service import delete_document
            try:
                delete_document(db, doc.id)
            except Exception as e:
                logger.warning("Error eliminando doc previo Wasi %s: %s", doc.id, e)

        # Crear contenido del inventario
        content_lines = ["=== INVENTARIO INMOBILIARIO WASI ===\n"]
        content_lines.append(
            "Este es el catálogo REAL y ACTUAL de propiedades disponibles. "
            "SIEMPRE usa estos datos para recomendar propiedades. "
            "NUNCA inventes precios, áreas ni links.\n"
        )
        for i, prop in enumerate(properties, 1):
            content_lines.append(f"\n--- PROPIEDAD {i} ---")
            content_lines.append(_property_to_text(prop))

        full_content = "\n".join(content_lines)
        title = f"INVENTARIO_WASI_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}"

        # Indexar el documento completo
        await index_document(
            db=db,
            agent_id=agent.id,
            title=title,
            content=full_content,
            content_type="text/plain",
            tenant_id=agent.tenant_id,
        )

        logger.info("Wasi sync: %d propiedades indexadas para agente %s", len(properties), agent.id)
        return len(properties), f"{len(properties)} propiedades sincronizadas exitosamente."

    except Exception as e:
        logger.error("Wasi sync_inventory error: %s", e, exc_info=True)
        return 0, f"Error en sincronización: {str(e)}"


async def create_wasi_lead(
    company_id: str,
    wasi_token: str,
    lead_data: dict,
) -> bool:
    """
    Crea un cliente/lead en el CRM de Wasi.co.

    Args:
        company_id: ID empresa Wasi.
        wasi_token: Token de acceso Wasi.
        lead_data: Datos del lead (name, email, phone, observations).

    Returns:
        True si el lead fue creado, False en caso contrario.
    """
    try:
        payload = _build_params(company_id, wasi_token, {
            "name": lead_data.get("name", lead_data.get("nombre", "")),
            "email": lead_data.get("email", lead_data.get("correo", "")),
            "phone": lead_data.get("telefono", lead_data.get("phone", "")),
            "observations": (
                f"Lead capturado por agente IA GENIA.\n"
                f"Tipo buscado: {lead_data.get('tipo_propiedad', 'N/A')}\n"
                f"Propósito: {lead_data.get('proposito', 'N/A')}\n"
                f"Presupuesto: {lead_data.get('presupuesto', 'N/A')}\n"
                f"Zona de interés: {lead_data.get('zona_interes', 'N/A')}"
            ),
        })
        async with httpx.AsyncClient(timeout=WASI_TIMEOUT) as client:
            resp = await client.post(
                f"{WASI_BASE_URL}/client/add",
                data=payload,
            )
            data = resp.json()
            success = data.get("status") == "success"
            if success:
                logger.info("Lead creado en Wasi CRM para company %s: %s", company_id, data)
            else:
                logger.warning("No se pudo crear lead en Wasi: %s", data)
            return success
    except Exception as e:
        logger.error("Wasi create_wasi_lead error: %s", e)
        return False
