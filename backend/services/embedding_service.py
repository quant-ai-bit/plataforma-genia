"""
Servicio de Embeddings para PLATAFORMA GENIA.

Utiliza Google Vertex AI (Google Cloud) como proveedor primario y Google Generative AI
(Gemini API Studio) como fallback para generar vectores numéricos de 768 dimensiones.
"""

import json
import logging
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)


def _get_vertex_embeddings(
    texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT"
) -> list[list[float]]:
    """
    Genera vectores de embedding utilizando la API de Google Cloud Vertex AI (text-embedding-004).

    Resuelve credenciales desde GCP_SERVICE_ACCOUNT_JSON, GOOGLE_APPLICATION_CREDENTIALS
    o Application Default Credentials (ADC).
    """
    import google.auth
    from google.auth.transport.requests import Request

    import os
    raw_json = getattr(settings, "gcp_service_account_json", "") or ""
    cred_path = getattr(settings, "google_application_credentials", "") or ""
    project = getattr(settings, "google_cloud_project", "") or ""
    location = getattr(settings, "google_cloud_location", "") or "us-central1"

    creds = None
    if raw_json.strip():
        from google.oauth2 import service_account

        info = json.loads(raw_json)
        if isinstance(info, dict) and "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        if not project and "project_id" in info:
            project = info["project_id"]
    elif cred_path.strip() and os.path.exists(cred_path):
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(
            cred_path, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
    else:
        creds, default_proj = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        project = project or default_proj

    if not creds:
        raise ValueError("No se pudieron resolver credenciales de GCP / Vertex AI.")

    creds.refresh(Request())
    token = creds.token

    if not project:
        raise ValueError("GOOGLE_CLOUD_PROJECT no configurado para Vertex AI.")

    task_type_upper = task_type.upper()
    url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models/text-embedding-004:predict"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    all_embeddings = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        instances = [{"content": t, "task_type": task_type_upper} for t in batch]
        payload = {
            "instances": instances,
            "parameters": {"outputDimensionality": 768},
        }
        res = httpx.post(url, json=payload, headers=headers, timeout=30.0)
        res.raise_for_status()
        data = res.json()

        for pred in data.get("predictions", []):
            vals = pred.get("embeddings", {}).get("values", [])
            all_embeddings.append(vals)

    return all_embeddings


def get_embeddings(
    texts: list[str], task_type: str = "retrieval_document"
) -> list[list[float]]:
    """
    Genera vectores de embedding para una lista de textos.

    Soporta Google Cloud Vertex AI (primario) y Google AI Studio (fallback).

    Args:
        texts: Lista de textos a procesar.
        task_type: Tipo de tarea de embedding.

    Returns:
        Lista de vectores de embedding de 768 dimensiones.
    """
    if not texts:
        return []

    # 1. Intentar proveedor primario: Vertex AI (Google Cloud)
    try:
        logger.info("Generando embeddings via Vertex AI (Google Cloud)...")
        return _get_vertex_embeddings(texts, task_type=task_type)
    except Exception as e_vertex:
        logger.warning(
            "Fallo al generar embeddings con Vertex AI (%s). Probando fallback a Google AI Studio...",
            str(e_vertex),
        )

    # 2. Fallback: Google AI Studio SDK (gemini-embedding-001 / text-embedding-004)
    if settings.gemini_api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            result = genai.embed_content(
                model="models/gemini-embedding-001",
                content=texts,
                task_type=task_type,
                output_dimensionality=768,
            )
            return result["embedding"]
        except Exception as e_gemini:
            logger.error("Error al generar embeddings en batch con Gemini API Studio: %s", str(e_gemini), exc_info=True)
            raise e_gemini

    raise RuntimeError(
        "No se pudieron generar los embeddings: Vertex AI falló y no hay GEMINI_API_KEY válida configurada."
    )


def get_embedding(
    text: str, task_type: str = "retrieval_document"
) -> list[float]:
    """
    Genera el vector de embedding para una sola cadena de texto.

    Args:
        text: Texto a procesar.
        task_type: Tipo de tarea de embedding.

    Returns:
        Lista de floats (768 dimensiones).
    """
    if not text.strip():
        return []

    embeddings = get_embeddings([text], task_type=task_type)
    return embeddings[0] if embeddings else []
