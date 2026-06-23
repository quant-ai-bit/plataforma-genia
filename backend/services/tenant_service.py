"""
tenant_service: acceso a la entidad Tenant para la plataforma multi-tenant.

Provee consultas de lectura acotadas por tenant (`get` por id, `get_by_slug`
por slug unico) y un helper `is_active` para verificar el estado del tenant.
Todas las consultas estan limitadas explicitamente al tenant solicitado para
garantizar el aislamiento de datos.

Feature: genia-agent-platform (Tarea 3.1)
"""

import logging

from sqlalchemy.orm import Session

from models.tenant import Tenant

logger = logging.getLogger(__name__)


def get(db: Session, tenant_id: str) -> Tenant | None:
    """
    Recupera un tenant por su identificador unico.

    Args:
        db: Sesion de base de datos.
        tenant_id: Identificador (UUID hex) del tenant.

    Returns:
        El `Tenant` correspondiente o `None` si no existe.
    """
    if not tenant_id:
        return None
    return db.query(Tenant).filter(Tenant.id == tenant_id).first()


def get_by_slug(db: Session, slug: str) -> Tenant | None:
    """
    Recupera un tenant por su slug unico.

    Args:
        db: Sesion de base de datos.
        slug: Slug unico del tenant (usado para idempotencia).

    Returns:
        El `Tenant` correspondiente o `None` si no existe.
    """
    if not slug:
        return None
    return db.query(Tenant).filter(Tenant.slug == slug).first()


def is_active(tenant: Tenant | None) -> bool:
    """
    Indica si un tenant existe y esta activo.

    Args:
        tenant: Instancia de `Tenant` o `None`.

    Returns:
        True si el tenant no es None y su campo `is_active` es verdadero.
    """
    return bool(tenant is not None and tenant.is_active)

def upsert_by_slug(db: Session, name: str, slug: str) -> Tenant:
    """
    Crea o recupera (idempotente) un tenant por su slug unico.

    Si ya existe un tenant con ese `slug` lo devuelve actualizando su `name` e
    `is_active=True`; si no, lo crea. La idempotencia se basa en el slug unico,
    de modo que re-ejecutar el aprovisionamiento no duplica el tenant.

    Args:
        db: Sesion de base de datos.
        name: Nombre visible del tenant.
        slug: Slug unico (clave de idempotencia).

    Returns:
        El `Tenant` creado o ya existente.
    """
    tenant = get_by_slug(db, slug)
    if tenant is not None:
        changed = False
        if name and tenant.name != name:
            tenant.name = name
            changed = True
        if not tenant.is_active:
            tenant.is_active = True
            changed = True
        if changed:
            db.flush()
        return tenant
    tenant = Tenant(name=name or slug, slug=slug, is_active=True)
    db.add(tenant)
    db.flush()
    logger.info("Tenant creado por aprovisionamiento (slug=%s)", slug)
    return tenant
