"""
Servicio multi-proveedor de transcripción de voz (STT) para PLATAFORMA GENIA.

Soporta múltiples proveedores de Speech-to-Text, seleccionables por agente:
- Groq Whisper (whisper-large-v3) — por defecto
- Google Cloud Speech-to-Text
- Deepgram (Nova-3)
- OpenAI Whisper API

El agente configura su proveedor STT preferido en su configuración.
Todos los proveedores optimizados para español.
"""

import logging
from io import BytesIO

from config import settings

logger = logging.getLogger(__name__)

# Proveedores soportados con info para el frontend
STT_PROVIDERS = {
    "groq_whisper": {
        "name": "Groq Whisper",
        "description": "Whisper Large V3 via Groq — Rápido y preciso para español",
        "model": "whisper-large-v3",
        "requires_key": "GROQ_API_KEY",
        "cost_per_minute": 0.006,
    },
    "openai_whisper": {
        "name": "OpenAI Whisper",
        "description": "Whisper via API de OpenAI — Alta precisión multilingüe",
        "model": "whisper-1",
        "requires_key": "OPENAI_API_KEY",
        "cost_per_minute": 0.006,
    },
    "deepgram": {
        "name": "Deepgram Nova-3",
        "description": "Nova-3 — Baja latencia, ideal para conversaciones en tiempo real",
        "model": "nova-3",
        "requires_key": "DEEPGRAM_API_KEY",
        "cost_per_minute": 0.0048,
    },
    "google_stt": {
        "name": "Google Cloud STT",
        "description": "Google Cloud Speech-to-Text — Integración con ecosistema GCP",
        "model": "latest_long",
        "requires_key": "GEMINI_API_KEY",
        "cost_per_minute": 0.009,
    },
}


async def transcribe_audio(
    audio_bytes: bytes,
    mime_type: str = "audio/ogg",
    filename: str = "voice.ogg",
    stt_provider: str = "groq_whisper",
    language: str = "es",
) -> str:
    """
    Transcribe audio a texto usando el proveedor STT especificado.

    Args:
        audio_bytes: Bytes del archivo de audio.
        mime_type: Tipo MIME del audio.
        filename: Nombre del archivo.
        stt_provider: Proveedor STT a usar.
        language: Código de idioma (default: 'es' para español).

    Returns:
        Texto transcrito.

    Raises:
        ValueError: Si el proveedor no está soportado o configurado.
    """
    # Sanitizar mime_type para remover parámetros adicionales como codecs o espacios
    if mime_type and ";" in mime_type:
        mime_type = mime_type.split(";")[0].strip()

    if stt_provider not in STT_PROVIDERS:
        logger.warning(
            "Proveedor STT '%s' no reconocido. Usando fallback 'groq_whisper'.",
            stt_provider,
        )
        stt_provider = "groq_whisper"

    logger.info(
        "Transcribiendo audio (%s, %d bytes) con proveedor '%s'...",
        mime_type,
        len(audio_bytes),
        stt_provider,
    )

    try:
        if stt_provider == "groq_whisper":
            return await _transcribe_groq_whisper(audio_bytes, mime_type, filename, language)
        elif stt_provider == "openai_whisper":
            return await _transcribe_openai_whisper(audio_bytes, mime_type, filename, language)
        elif stt_provider == "deepgram":
            return await _transcribe_deepgram(audio_bytes, mime_type, language)
        elif stt_provider == "google_stt":
            return await _transcribe_google_stt(audio_bytes, mime_type, language)
        else:
            return await _transcribe_groq_whisper(audio_bytes, mime_type, filename, language)
    except Exception as e:
        logger.error(
            "Error transcribiendo con '%s': %s. Intentando fallback...",
            stt_provider,
            str(e),
        )
        # Fallback: intentar con groq_whisper si el proveedor principal falla
        if stt_provider != "groq_whisper":
            try:
                logger.info("Ejecutando fallback STT con groq_whisper...")
                return await _transcribe_groq_whisper(audio_bytes, mime_type, filename, language)
            except Exception as fallback_error:
                logger.error("Fallback STT también falló: %s", str(fallback_error))
                raise fallback_error
        raise e


async def _transcribe_groq_whisper(
    audio_bytes: bytes,
    mime_type: str,
    filename: str,
    language: str,
) -> str:
    """Transcribe audio usando la API Whisper de Groq."""
    from groq import AsyncGroq

    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY no configurada para transcripción Whisper.")

    client = AsyncGroq(api_key=settings.groq_api_key)
    file_tuple = (filename, BytesIO(audio_bytes), mime_type)

    response = await client.audio.transcriptions.create(
        file=file_tuple,
        model="whisper-large-v3",
        language=language,
    )
    return response.text


async def _transcribe_openai_whisper(
    audio_bytes: bytes,
    mime_type: str,
    filename: str,
    language: str,
) -> str:
    """Transcribe audio usando la API Whisper de OpenAI."""
    from openai import AsyncOpenAI

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY no configurada para transcripción Whisper.")

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    file_tuple = (filename, BytesIO(audio_bytes), mime_type)

    response = await client.audio.transcriptions.create(
        file=file_tuple,
        model="whisper-1",
        language=language,
    )
    return response.text


async def _transcribe_deepgram(
    audio_bytes: bytes,
    mime_type: str,
    language: str,
) -> str:
    """Transcribe audio usando la API de Deepgram Nova-3."""
    import httpx

    if not settings.deepgram_api_key:
        raise ValueError("DEEPGRAM_API_KEY no configurada para transcripción.")

    url = "https://api.deepgram.com/v1/listen"
    headers = {
        "Authorization": f"Token {settings.deepgram_api_key}",
        "Content-Type": mime_type,
    }
    params = {
        "model": "nova-3",
        "language": language,
        "smart_format": "true",
        "punctuate": "true",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            headers=headers,
            params=params,
            content=audio_bytes,
        )
        response.raise_for_status()
        result = response.json()

    # Extraer transcripción del resultado de Deepgram
    channels = result.get("results", {}).get("channels", [])
    if channels:
        alternatives = channels[0].get("alternatives", [])
        if alternatives:
            return alternatives[0].get("transcript", "")

    return ""


async def _transcribe_google_stt(
    audio_bytes: bytes,
    mime_type: str,
    language: str,
) -> str:
    """Transcribe audio usando Google Cloud Speech-to-Text v1."""
    import httpx
    import base64

    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY no configurada para Google Cloud Speech-to-Text."
        )

    # Mapear MIME type a encoding de Google STT
    encoding_map = {
        "audio/ogg": "OGG_OPUS",
        "audio/webm": "WEBM_OPUS",
        "audio/mpeg": "MP3",
        "audio/mp3": "MP3",
        "audio/wav": "LINEAR16",
        "audio/flac": "FLAC",
        "audio/m4a": "MP3",
    }
    encoding = encoding_map.get(mime_type, "OGG_OPUS")

    # Mapear código de idioma
    language_code = "es-CO" if language == "es" else f"{language}-{language.upper()}"

    url = f"https://speech.googleapis.com/v1/speech:recognize?key={settings.gemini_api_key}"
    payload = {
        "config": {
            "encoding": encoding,
            "languageCode": language_code,
            "enableAutomaticPunctuation": True,
            "model": "latest_long",
            "alternativeLanguageCodes": ["es-MX", "es-ES"],
        },
        "audio": {
            "content": base64.b64encode(audio_bytes).decode("utf-8"),
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        result = response.json()

    results = result.get("results", [])
    if results:
        alternatives = results[0].get("alternatives", [])
        if alternatives:
            return alternatives[0].get("transcript", "")

    return ""


def get_available_providers() -> list[dict]:
    """
    Retorna la lista de proveedores STT disponibles con su info.
    Útil para poblar el selector en el frontend.
    """
    providers = []
    for key, info in STT_PROVIDERS.items():
        providers.append({
            "id": key,
            "name": info["name"],
            "description": info["description"],
            "model": info["model"],
            "cost_per_minute": info["cost_per_minute"],
        })
    return providers
