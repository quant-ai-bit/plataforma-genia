"""
Router de Base de Conocimiento para PLATAFORMA GENIA.

Permite a los usuarios cargar archivos de texto o PDF para la base de conocimiento
de un agente, listar documentos cargados y eliminarlos.
"""

import logging
import uuid
import re
import os
import shutil
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.agent import Agent
from models.knowledge import KnowledgeDocument
from models.agent_image import AgentImage
from schemas.knowledge import KnowledgeDocumentDetail, KnowledgeDocumentResponse
from schemas.agent_image import AgentImageResponse
from services.knowledge_service import delete_document, process_and_index_document
from services.vision_service import analyze_image_for_agent, generate_image_training_rule
from services.storage_service import upload_file

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Knowledge Base"])


class ManualTextCreate(BaseModel):
    """Esquema para crear un documento de conocimiento a partir de texto manual."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Título o nombre descriptivo del documento",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Contenido textual de conocimiento para indexar",
    )


class ManualTextUpdate(BaseModel):
    """Esquema para actualizar un documento de conocimiento."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Título o nombre descriptivo del documento",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Contenido del documento en texto plano",
    )


class ConfirmTrainingRequest(BaseModel):
    """Esquema para confirmar el entrenamiento de una imagen y actualizar el prompt."""

    description: str = Field(..., description="Descripción final de la imagen")
    detected_product: str = Field(..., description="Nombre del producto/servicio detectado")
    keywords: str = Field(..., description="Palabras clave para activar esta imagen")
    suggested_rule: str = Field(..., description="Instrucción de prompt recomendada")
    add_to_prompt: bool = Field(True, description="Si se debe inyectar la instrucción en el prompt del sistema")


@router.post(
    "/agents/{agent_id}/documents/text",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_manual_text_document(
    agent_id: str,
    payload: ManualTextCreate,
    db: Session = Depends(get_db),
):
    """
    Agrega un documento de conocimiento de forma manual ingresando texto plano.

    El texto es segmentado en chunks e indexado en ChromaDB para el agente.
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún agente con el ID {agent_id}",
        )

    try:
        # Convertir a bytes de texto plano UTF-8 para reusar el servicio
        file_bytes = payload.content.encode("utf-8")
        filename = payload.title
        if not filename.endswith(".txt"):
            filename += ".txt"

        db_doc = process_and_index_document(
            db=db,
            agent_id=agent_id,
            filename=filename,
            content_type="text/plain",
            file_bytes=file_bytes,
        )
        return db_doc

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(
            "Error al guardar texto manual para el agente %s: %s",
            agent_id,
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar e indexar el texto: {str(e)}",
        )



@router.post(
    "/agents/{agent_id}/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    agent_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Carga un documento (TXT, PDF, etc.) para alimentar la base de conocimiento de un agente.

    El archivo es procesado en fragmentos y vectorizado en ChromaDB de forma síncrona.
    """
    # 1. Verificar si el agente existe
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún agente con el ID {agent_id}",
        )

    # 2. Leer contenido del archivo
    try:
        file_bytes = await file.read()
        filename = file.filename or "archivo_sin_nombre"
        content_type = file.content_type or "text/plain"

        logger.info(
            "Recibido archivo '%s' (%s) para el agente %s.",
            filename,
            content_type,
            agent_id,
        )

        # 3. Procesar y guardar (SQL + Chroma)
        db_doc = process_and_index_document(
            db=db,
            agent_id=agent_id,
            filename=filename,
            content_type=content_type,
            file_bytes=file_bytes,
        )
        return db_doc

    except ValueError as ve:
        logger.warning(
            "Error de validación al procesar documento: %s", str(ve)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(
            "Error interno procesando documento: %s", str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar e indexar el documento: {str(e)}",
        )


@router.get(
    "/agents/{agent_id}/documents",
    response_model=list[KnowledgeDocumentResponse],
)
def list_agent_documents(agent_id: str, db: Session = Depends(get_db)):
    """Lista todos los documentos de conocimiento cargados para un agente específico."""
    # Verificar si el agente existe
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún agente con el ID {agent_id}",
        )

    documents = (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.agent_id == agent_id)
        .order_by(KnowledgeDocument.uploaded_at.desc())
        .all()
    )
    return documents


@router.get("/documents/{doc_id}", response_model=KnowledgeDocumentDetail)
def get_document_detail(doc_id: str, db: Session = Depends(get_db)):
    """Obtiene el detalle completo de un documento de conocimiento, incluyendo su texto crudo."""
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún documento con el ID {doc_id}",
        )
    return doc


@router.delete("/documents/{doc_id}", status_code=status.HTTP_200_OK)
def delete_agent_document(doc_id: str, db: Session = Depends(get_db)):
    """Elimina un documento de conocimiento de SQL y de la base vectorial ChromaDB."""
    success = delete_document(db=db, doc_id=doc_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún documento con el ID {doc_id}",
        )
    return {
        "status": "success",
        "message": f"Documento {doc_id} eliminado exitosamente.",
    }


@router.put(
    "/documents/{doc_id}",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_200_OK,
)
async def update_manual_text_document(
    doc_id: str,
    payload: ManualTextUpdate,
    db: Session = Depends(get_db),
):
    """
    Actualiza el título y el contenido de un documento de conocimiento en SQL y ChromaDB.
    """
    try:
        from services.knowledge_service import update_document_content
        filename = payload.title
        if not filename.endswith(".txt"):
            filename += ".txt"
        db_doc = update_document_content(
            db=db,
            doc_id=doc_id,
            filename=filename,
            new_content=payload.content,
        )
        return db_doc
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(
            "Error al actualizar documento de conocimiento %s: %s",
            doc_id,
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el documento: {str(e)}",
        )


# ── Endpoints para la Biblioteca de Imágenes ────────────────────────────

@router.post(
    "/agents/{agent_id}/images",
    response_model=AgentImageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_agent_image(
    agent_id: str,
    request: Request,
    file: UploadFile = File(...),
    description: str = Form(None),
    db: Session = Depends(get_db),
):
    """
    Sube una imagen para la biblioteca de un agente (no para RAG).
    Sube a Supabase Storage o localmente según configuración.
    """
    # 1. Verificar si el agente existe
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún agente con el ID {agent_id}",
        )

    # 2. Validar que el archivo sea una imagen
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo cargado debe ser una imagen (PNG, JPG, JPEG, etc.).",
        )

    # 3. Guardar el archivo en almacenamiento
    try:
        file_bytes = await file.read()
        ext = os.path.splitext(file.filename or "")[1] or ".png"
        unique_filename = f"{agent_id}_{uuid.uuid4().hex}{ext}"

        public_url = await upload_file(
            file_bytes=file_bytes,
            filename=unique_filename,
            content_type=file.content_type,
            bucket="agent-images",
        )

        # Si es URL relativa, agregar la base URL dinámica
        if public_url.startswith("/"):
            base_url = str(request.base_url).rstrip("/")
            public_url = f"{base_url}{public_url}"

        # 4. Registrar en base de datos
        db_image = AgentImage(
            agent_id=agent_id,
            filename=file.filename or "imagen_sin_nombre",
            description=description,
            url=public_url,
        )
        db.add(db_image)
        db.commit()
        db.refresh(db_image)
        
        logger.info(
            "Imagen '%s' subida correctamente para el agente %s (URL: %s)",
            db_image.filename,
            agent_id,
            public_url
        )
        return db_image

    except Exception as e:
        logger.error("Error al subir imagen para el agente %s: %s", agent_id, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al guardar la imagen: {str(e)}",
        )


@router.get(
    "/agents/{agent_id}/images",
    response_model=list[AgentImageResponse],
)
def list_agent_images(agent_id: str, db: Session = Depends(get_db)):
    """Lista todas las imágenes de la biblioteca de un agente específico."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún agente con el ID {agent_id}",
        )

    images = (
        db.query(AgentImage)
        .filter(AgentImage.agent_id == agent_id)
        .order_by(AgentImage.uploaded_at.desc())
        .all()
    )
    return images


@router.post(
    "/agents/{agent_id}/images/upload-and-generate-training",
    status_code=status.HTTP_201_CREATED,
)
async def upload_and_generate_training(
    agent_id: str,
    request: Request,
    file: UploadFile = File(...),
    product_name: str = Form(...),
    description: str = Form(...),
    price: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Sube una imagen, la guarda en almacenamiento (Supabase o local), crea un registro temporal
    en la base de datos con la descripción combinada (Nombre, Descripción, Precio)
    y utiliza Gemini para sugerir reglas de prompt y palabras clave.
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún agente con el ID {agent_id}",
        )

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo cargado debe ser una imagen (PNG, JPG, JPEG, etc.).",
        )

    try:
        # Leer bytes del archivo para guardar
        file_bytes = await file.read()
        
        # Guardar archivo en almacenamiento
        ext = os.path.splitext(file.filename or "")[1] or ".png"
        unique_filename = f"{agent_id}_{uuid.uuid4().hex}{ext}"

        public_url = await upload_file(
            file_bytes=file_bytes,
            filename=unique_filename,
            content_type=file.content_type,
            bucket="agent-images",
        )

        # Si es URL relativa, agregar la base URL dinámica
        if public_url.startswith("/"):
            base_url = str(request.base_url).rstrip("/")
            public_url = f"{base_url}{public_url}"
        
        # Registrar en la base de datos con formato compatible
        combined_desc = f"{product_name} - Precio: {price}. {description}"
        db_image = AgentImage(
            agent_id=agent_id,
            filename=file.filename or "imagen_sin_nombre",
            description=combined_desc,
            url=public_url,
        )
        db.add(db_image)
        db.commit()
        db.refresh(db_image)

        # Utilizar Gemini LLM para generar reglas de prompt y keywords
        analysis = generate_image_training_rule(
            product_name=product_name,
            description=description,
            price=price,
            url=db_image.url
        )

        return {
            "image_id": db_image.id,
            "url": db_image.url,
            "filename": db_image.filename,
            "detected_product": product_name,
            "description": combined_desc,
            "keywords": analysis.get("keywords", ""),
            "suggested_rule": analysis.get("suggested_rule", "")
        }

    except Exception as e:
        logger.error("Error al subir y generar entrenamiento para el agente %s: %s", agent_id, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en la generación de entrenamiento: {str(e)}",
        )


@router.post(
    "/agents/{agent_id}/images/{image_id}/confirm-training",
    status_code=status.HTTP_200_OK,
)
def confirm_image_training(
    agent_id: str,
    image_id: str,
    payload: ConfirmTrainingRequest,
    db: Session = Depends(get_db),
):
    """
    Confirma la descripción de la imagen y la regla de prompt, guardando la
    descripción definitiva y actualizando el system prompt del agente.
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún agente con el ID {agent_id}",
        )

    db_image = db.query(AgentImage).filter(AgentImage.id == image_id, AgentImage.agent_id == agent_id).first()
    if not db_image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ninguna imagen con el ID {image_id} para este agente.",
        )

    # Actualizar descripción en base de datos
    db_image.description = payload.description
    db.commit()

    if payload.add_to_prompt:
        try:
            # Reemplazar placeholder {url} en la regla si existe
            final_rule = payload.suggested_rule
            if "{url}" in final_rule:
                final_rule = final_rule.replace("{url}", db_image.url)

            # Limpiar cualquier regla previa de esta imagen en el system_prompt
            current_prompt = agent.system_prompt or ""
            pattern = re.compile(
                rf"\s*<!-- START_IMAGE_RULE:{image_id} -->.*?<!-- END_IMAGE_RULE:{image_id} -->",
                re.DOTALL
            )
            cleaned_prompt = pattern.sub("", current_prompt).strip()

            # Construir bloque de regla nuevo
            rule_block = (
                f"\n\n<!-- START_IMAGE_RULE:{image_id} -->\n"
                f"{final_rule}\n"
                f"<!-- END_IMAGE_RULE:{image_id} -->"
            )

            # Actualizar prompt del agente
            agent.system_prompt = (cleaned_prompt + rule_block).strip()
            db.commit()
            logger.info("Entrenamiento visual guardado y prompt actualizado para imagen %s del agente %s.", image_id, agent_id)
        except Exception as e:
            logger.error("Error al inyectar regla en el prompt para imagen %s: %s", image_id, str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al actualizar el prompt del agente: {str(e)}",
            )

    return {
        "status": "success",
        "message": "Entrenamiento de imagen completado con éxito.",
        "image": {
            "id": db_image.id,
            "description": db_image.description,
            "url": db_image.url
        }
    }


@router.delete("/images/{image_id}", status_code=status.HTTP_200_OK)
def delete_agent_image(image_id: str, db: Session = Depends(get_db)):
    """Elimina una imagen de la biblioteca del agente (de la DB y del disco)."""
    db_image = db.query(AgentImage).filter(AgentImage.id == image_id).first()
    if not db_image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ninguna imagen con el ID {image_id}",
        )

    # 1. Limpiar del system prompt del agente si tiene alguna regla vinculada a esta imagen
    try:
        agent = db_image.agent
        if agent and agent.system_prompt:
            pattern = re.compile(
                rf"\s*<!-- START_IMAGE_RULE:{image_id} -->.*?<!-- END_IMAGE_RULE:{image_id} -->",
                re.DOTALL
            )
            new_prompt, count = pattern.subn("", agent.system_prompt)
            if count > 0:
                agent.system_prompt = new_prompt.strip()
                db.add(agent)
                logger.info("Reglas de prompt para imagen %s removidas del agente %s.", image_id, agent.id)
    except Exception as e:
        logger.error("Error al intentar limpiar el system prompt para imagen %s: %s", image_id, str(e))

    # 2. Eliminar archivo físico
    try:
        filename = db_image.url.split("/")[-1]
        filepath = os.path.join("data/uploads", filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info("Archivo físico de imagen eliminado: %s", filepath)
    except Exception as e:
        logger.warning("No se pudo eliminar el archivo físico de la imagen %s: %s", image_id, str(e))

    # 3. Eliminar registro de base de datos
    db.delete(db_image)
    db.commit()
    logger.info("Registro de imagen %s eliminado de la base de datos.", image_id)
    return {
        "status": "success",
        "message": f"Imagen {image_id} eliminada exitosamente.",
    }

