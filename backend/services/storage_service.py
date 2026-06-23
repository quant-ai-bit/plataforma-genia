"""Servicio de Almacenamiento (Supabase Storage) para PLATAFORMA GENIA."""

import os
import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)


async def upload_file(file_bytes: bytes, filename: str, content_type: str, bucket: str = "agent-images") -> str:
    """
    Sube un archivo al almacenamiento.
    
    Si Supabase está configurado (URL y Service Key disponibles), sube el archivo
    a Supabase Storage en el bucket indicado y retorna la URL pública.
    De lo contrario, guarda el archivo localmente en el disco (data/uploads)
    y retorna la ruta estática local.
    """
    use_supabase = bool(settings.supabase_url and settings.supabase_service_key)

    if use_supabase:
        try:
            # Limpiar el nombre del archivo para evitar caracteres problemáticos en URLs
            clean_filename = filename.replace(" ", "_")
            url = f"{settings.supabase_url}/storage/v1/object/{bucket}/{clean_filename}"
            headers = {
                "Authorization": f"Bearer {settings.supabase_service_key}",
                "Content-Type": content_type or "application/octet-stream",
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, content=file_bytes, headers=headers)
                
                # Si el archivo ya existe, intentamos sobrescribirlo con PUT
                if response.status_code == 400 and "already exists" in response.text.lower():
                    logger.info("El archivo %s ya existe. Intentando sobrescribir con PUT...", clean_filename)
                    response = await client.put(url, content=file_bytes, headers=headers)
                
                response.raise_for_status()

            # URL pública en Supabase
            public_url = f"{settings.supabase_url}/storage/v1/object/public/{bucket}/{clean_filename}"
            logger.info("Archivo subido a Supabase Storage: %s", public_url)
            return public_url

        except Exception as e:
            logger.error(
                "Error al subir a Supabase Storage: %s. Usando fallback local.",
                str(e),
                exc_info=True
            )
            # Caemos en el fallback local si ocurre un error

    # Fallback local: guardar en data/uploads/
    os.makedirs("data/uploads", exist_ok=True)
    filepath = os.path.join("data/uploads", filename)
    
    try:
        with open(filepath, "wb") as f:
            f.write(file_bytes)
        logger.info("Archivo guardado localmente (fallback): %s", filepath)
        return f"/static/uploads/{filename}"
    except Exception as e:
        logger.error("Error al guardar archivo localmente: %s", str(e), exc_info=True)
        raise RuntimeError(f"No se pudo guardar el archivo: {str(e)}")
