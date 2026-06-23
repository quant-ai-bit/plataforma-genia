"""
seed_tenant.py: aprovisionamiento idempotente de un tenant desde un YAML.

Carga una especificacion declarativa (por defecto
`provisioning/con-tranqui.yaml`), construye un `TenantSpec` e invoca el
`Provisioning_Service`. Pensado para el arranque local/CI y el bootstrap del
primer tenant (con-tranqui). Es idempotente: re-ejecutar no duplica entidades
ni re-emite la API key (salvo `--rotate-api-key`).

Uso:
    python -m scripts.seed_tenant
    python scripts/seed_tenant.py --file provisioning/con-tranqui.yaml
    python scripts/seed_tenant.py --rotate-api-key

Feature: genia-agent-platform (Tarea 14.4)
"""

import argparse
import asyncio
import logging
import os
import sys

# Permitir ejecutar el script directamente (anade backend/ al path).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml  # noqa: E402

from database import SessionLocal  # noqa: E402
from services.provisioning_service import (  # noqa: E402
    ProvisioningService,
    TenantSpec,
)

logger = logging.getLogger(__name__)

DEFAULT_SPEC_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "provisioning",
    "con-tranqui.yaml",
)


def load_spec(path: str) -> TenantSpec:
    """Carga un archivo YAML declarativo y construye un `TenantSpec`."""
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return TenantSpec(
        name=data["name"],
        slug=data["slug"],
        system_prompt=data.get("system_prompt", ""),
        model=data.get("model"),
        model_params=data.get("model_params") or {},
        enabled_mcp_tools=data.get("enabled_mcp_tools") or [],
        mcp_server_url_env=data.get("mcp_server_url_env"),
        mcp_service_token_env=data.get("mcp_service_token_env"),
        subscription_plan=data.get("subscription_plan"),
        knowledge_collection=data.get("knowledge_collection"),
    )


async def seed(path: str, rotate_api_key: bool = False) -> dict:
    """Aprovisiona el tenant descrito en `path` y devuelve el resultado publico."""
    spec = load_spec(path)
    db = SessionLocal()
    try:
        result = await ProvisioningService().provision(
            spec, db, rotate_api_key=rotate_api_key
        )
        db.commit()
        return result.to_public_dict()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    """Punto de entrada CLI del seed de tenant."""
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Aprovisiona un tenant desde un YAML.")
    parser.add_argument(
        "--file",
        default=DEFAULT_SPEC_PATH,
        help="Ruta al YAML declarativo del tenant.",
    )
    parser.add_argument(
        "--rotate-api-key",
        action="store_true",
        help="Rota (re-emite) la API key del tenant.",
    )
    args = parser.parse_args()

    result = asyncio.run(seed(args.file, rotate_api_key=args.rotate_api_key))
    secret = result.get("api_key")
    print("Tenant aprovisionado:", result.get("slug"), "(", result.get("tenant_id"), ")")
    if secret:
        print("API key (se muestra una sola vez):", secret)
    else:
        print("API key existente: no se re-emitio (usa --rotate-api-key para rotar).")


if __name__ == "__main__":
    main()
