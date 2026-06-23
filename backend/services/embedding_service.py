"""
Servicio de Embeddings para PLATAFORMA GENIA.

Utiliza la API de Google Gemini (modelo text-embedding-004) para generar
vectores numéricos de 768 dimensiones a partir de fragmentos de texto.
"""

import logging
from typing import Any

import google.generativeai as genai

from config import settings

logger = logging.getLogger(__name__)

# Configurar el SDK de Google Generative AI
if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)
else:
    logger.warning("GEMINI_API_KEY no está configurada en las variables de entorno.")


def get_embedding(
    text: str, task_type: str = "retrieval_document"
) -> list[float]:
    """
    Genera el vector de embedding para una sola cadena de texto.

    Args:
        text: Texto a procesar.
        task_type: Tipo de tarea de embedding. Por defecto 'retrieval_document'.
                   Se puede usar 'retrieval_query' para búsquedas de consulta.

    Returns:
        Lista de floats (768 dimensiones).
    """
    if not text.strip():
        return []

    try:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type=task_type,
        )
        return result["embedding"]
    except Exception as e:
        logger.error("Error al generar embedding con Gemini: %s", str(e), exc_info=True)
        # Retornar vector de ceros de 768 dims como fallback o levantar excepción?
        # Levantamos la excepción para que el proceso que lo invoca pueda manejar el fallo
        raise e


def get_embeddings(
    texts: list[str], task_type: str = "retrieval_document"
) -> list[list[float]]:
    """
    Genera vectores de embedding para una lista de textos.

    Optimiza la llamada procesando múltiples textos en batch.

    Args:
        texts: Lista de textos a procesar.
        task_type: Tipo de tarea de embedding.

    Returns:
        Lista de vectores de embedding.
    """
    if not texts:
        return []

    try:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=texts,
            task_type=task_type,
        )
        # La API devuelve una lista de diccionarios o una lista de embeddings
        # dependiendo del formato. En text-embedding-004 suele ser una lista directa.
        embeddings = result["embedding"]
        return embeddings
    except Exception as e:
        logger.error("Error al generar embeddings en batch con Gemini: %s", str(e), exc_info=True)
        raise e
