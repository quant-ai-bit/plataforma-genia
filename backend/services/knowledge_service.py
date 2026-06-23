"""
Servicio de Base de Conocimiento (RAG) para PLATAFORMA GENIA.

Gestiona la extracción de texto (TXT, PDF), la división en fragmentos (chunking),
la indexación en la base de datos vectorial ChromaDB utilizando embeddings de Gemini,
y la recuperación de contexto relevante (Retrieval) para responder preguntas.
"""

import io
import logging
import uuid

from PyPDF2 import PdfReader
from sqlalchemy.orm import Session

from config import settings
from database import is_sqlite
from models.knowledge import KnowledgeDocument
from services.embedding_service import get_embedding, get_embeddings

logger = logging.getLogger(__name__)

# ── Cliente de ChromaDB ──────────────────────────────────────────────
# Persistente en el directorio configurado (solo se inicializa si es SQLite)
chroma_client = None
if is_sqlite:
    import chromadb
    chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)


# ── Extracción de texto según formato ───────────────────────────────

def extract_text(content: bytes, content_type: str) -> str:
    """
    Extrae texto legible a partir de un archivo binario.

    Soporta text/plain, text/markdown y application/pdf.
    """
    if "text" in content_type or "markdown" in content_type:
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            # Fallback a latin-1 si UTF-8 falla
            return content.decode("latin-1")

    elif "pdf" in content_type:
        try:
            pdf_file = io.BytesIO(content)
            reader = PdfReader(pdf_file)
            text_parts = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error("Error al extraer texto del PDF: %s", str(e), exc_info=True)
            raise ValueError(f"No se pudo extraer texto del PDF: {str(e)}")

    else:
        # Intentar decodificar como texto por defecto
        try:
            return content.decode("utf-8")
        except Exception:
            raise ValueError(f"Tipo de contenido no soportado: {content_type}")


# ── Algoritmo de Chunking ───────────────────────────────────────────

def chunk_text(
    text: str, chunk_size: int = 800, chunk_overlap: int = 150
) -> list[str]:
    """
    Divide un texto largo en fragmentos más pequeños con solapamiento (sliding window).

    Args:
        text: Texto completo.
        chunk_size: Tamaño de cada fragmento en caracteres.
        chunk_overlap: Caracteres de solapamiento entre fragmentos consecutivos.

    Returns:
        Lista de fragmentos de texto.
    """
    if not text:
        return []

    # Limpieza básica
    text = text.strip()

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        # Avanzar la ventana
        start += chunk_size - chunk_overlap

        # Condición de salida de seguridad si el solapamiento es mayor o igual al size
        if chunk_size - chunk_overlap <= 0:
            break

    return chunks


# ── Procesamiento e indexación de documentos ─────────────────────────

def process_and_index_document(
    db: Session, agent_id: str, filename: str, content_type: str, file_bytes: bytes
) -> KnowledgeDocument:
    """
    Flujo E2E de inserción de documento:
    1. Extrae el texto del archivo.
    2. Divide en fragmentos (chunking).
    3. Genera embeddings con Gemini en batch.
    4. Guarda los vectores y metadatos en ChromaDB o pgvector.
    5. Guarda el registro del documento en la base de datos SQL.
    """
    # 1. Extraer texto
    raw_content = extract_text(file_bytes, content_type)
    if not raw_content.strip():
        raise ValueError("El archivo no contiene texto extraíble.")

    # 2. Fragmentar texto
    chunks = chunk_text(raw_content)
    chunk_count = len(chunks)
    logger.info(
        "Archivo '%s' fragmentado en %d chunks.", filename, chunk_count
    )

    # Resolver tenant_id del agente
    from models.agent import Agent
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    tenant_id = agent.tenant_id if agent else None

    # Crear el registro en SQL para obtener el ID del documento
    db_doc = KnowledgeDocument(
        agent_id=agent_id,
        tenant_id=tenant_id,
        filename=filename,
        content_type=content_type,
        raw_content=raw_content,
        chunk_count=chunk_count,
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    # 3 y 4. Indexar en Chroma o pgvector
    if chunk_count > 0:
        try:
            # Generar embeddings para todos los chunks
            embeddings = get_embeddings(chunks, task_type="retrieval_document")

            if is_sqlite:
                # Obtener colección de ChromaDB (per tenant si está configurado, o fallback por agente)
                if tenant_id:
                    collection_name = f"tenant_{tenant_id.replace('-', '_')}"
                else:
                    collection_name = f"agent_{agent_id.replace('-', '_')}"
                
                collection = chroma_client.get_or_create_collection(
                    name=collection_name
                )

                # Preparar listas para Chroma
                ids = [f"{db_doc.id}_{i}" for i in range(chunk_count)]
                metadatas = [
                    {
                        "document_id": db_doc.id,
                        "agent_id": agent_id,
                        "tenant_id": tenant_id or "",
                        "chunk_index": i,
                        "filename": filename,
                    }
                    for i in range(chunk_count)
                ]

                # Agregar a ChromaDB
                collection.add(
                    ids=ids,
                    documents=chunks,
                    embeddings=embeddings,
                    metadatas=metadatas,
                )
                logger.info(
                    "Indexados %d vectores en la colección '%s' de ChromaDB.",
                    chunk_count,
                    collection_name,
                )
            else:
                # pgvector
                from models.knowledge_chunk import KnowledgeChunk
                
                for i, chunk_text_content in enumerate(chunks):
                    chunk_embedding = embeddings[i]
                    db_chunk = KnowledgeChunk(
                        document_id=db_doc.id,
                        agent_id=agent_id,
                        tenant_id=tenant_id,
                        chunk_index=i,
                        content=chunk_text_content,
                        embedding=chunk_embedding
                    )
                    db.add(db_chunk)
                db.commit()
                logger.info(
                    "Indexados %d vectores para documento %s en tabla knowledge_chunks (pgvector).",
                    chunk_count,
                    db_doc.id,
                )

        except Exception as e:
            # Si falla la inserción en base vectorial, hacer rollback del registro SQL
            logger.error("Error al indexar en base vectorial: %s", str(e), exc_info=True)
            db.delete(db_doc)
            db.commit()
            raise RuntimeError(f"Error indexando en base vectorial: {str(e)}")

    return db_doc


# ── Eliminación de documentos ────────────────────────────────────────

def delete_document(db: Session, doc_id: str) -> bool:
    """
    Elimina un documento de la base de datos SQL y sus vectores asociados en Chroma o pgvector.
    """
    db_doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not db_doc:
        return False

    agent_id = db_doc.agent_id

    if is_sqlite:
        collection_name = f"agent_{agent_id.replace('-', '_')}"
        # Eliminar de ChromaDB
        try:
            collection = chroma_client.get_or_create_collection(name=collection_name)
            # Eliminar todos los chunks filtrando por metadato document_id
            collection.delete(where={"document_id": doc_id})
            logger.info(
                "Vectores del documento %s eliminados de ChromaDB (colección: %s).",
                doc_id,
                collection_name,
            )
        except Exception as e:
            logger.error(
                "Error eliminando vectores de ChromaDB para documento %s: %s",
                doc_id,
                str(e),
            )
    else:
        # pgvector (la eliminación cascade de base de datos se encarga, pero lo hacemos explícito para asegurar)
        try:
            from models.knowledge_chunk import KnowledgeChunk
            db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc_id).delete()
            logger.info(
                "Vectores del documento %s eliminados de la tabla knowledge_chunks (pgvector).",
                doc_id,
            )
        except Exception as e:
            logger.error(
                "Error eliminando vectores pgvector para documento %s: %s",
                doc_id,
                str(e),
            )

    # Eliminar de SQL
    db.delete(db_doc)
    db.commit()
    logger.info("Documento %s eliminado de la base de datos SQL.", doc_id)
    return True


# ── Búsqueda semántica (Retrieval) ───────────────────────────────────

def retrieve_context(agent_id: str, query: str, k: int = 4, db: Session = None) -> str:
    """
    Busca los fragmentos más relevantes para una consulta dada.
    Soporta ChromaDB (SQLite) o pgvector (PostgreSQL).

    Args:
        agent_id: ID del agente.
        query: Mensaje del usuario.
        k: Cantidad de fragmentos a retornar.
        db: Sesión opcional de base de datos. Si no se provee, se crea una temporal.

    Returns:
        Texto concatenado con la información contextual relevante.
    """
    if not query.strip():
        return ""

    db_session = db
    should_close = False
    if db_session is None:
        from database import SessionLocal
        db_session = SessionLocal()
        should_close = True

    try:
        if is_sqlite:
            # Obtener IDs de documentos activos en la base de datos SQL para este agente
            active_doc_ids = [
                row[0] for row in db_session.query(KnowledgeDocument.id)
                .filter(KnowledgeDocument.agent_id == agent_id)
                .all()
            ]

            # Si no hay documentos activos en SQL para este agente, no hay contexto que recuperar
            if not active_doc_ids:
                logger.info("El agente %s no tiene documentos activos en SQL. Retornando contexto vacío.", agent_id)
                return ""

            collection_name = f"agent_{agent_id.replace('-', '_')}"

            # Generar embedding para la consulta (retrieval_query)
            query_embedding = get_embedding(query, task_type="retrieval_query")

            # Obtener colección
            collection = chroma_client.get_collection(name=collection_name)

            # Filtrar por IDs de documentos activos
            if len(active_doc_ids) == 1:
                where_clause = {"document_id": active_doc_ids[0]}
            else:
                where_clause = {"document_id": {"$in": active_doc_ids}}

            # Consultar la colección
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where_clause,
            )

            # Formatear resultados
            documents = results.get("documents", [[]])[0]
            if not documents:
                return ""

            # Filtrar elementos que no sean cadenas de texto para evitar errores de tipo al unir
            documents = [doc for doc in documents if isinstance(doc, str)]
            if not documents:
                return ""

            # Unir fragmentos con un delimitador claro
            context = "\n\n---\n\n".join(documents)
            logger.info(
                "Búsqueda vectorial Chroma exitosa para agente %s. Retornados %d fragmentos.",
                agent_id,
                len(documents),
            )
            return context
        else:
            # pgvector (PostgreSQL)
            query_embedding = get_embedding(query, task_type="retrieval_query")
            
            from models.knowledge_chunk import KnowledgeChunk
            
            results = (
                db_session.query(KnowledgeChunk)
                .filter(KnowledgeChunk.agent_id == agent_id)
                .order_by(KnowledgeChunk.embedding.cosine_distance(query_embedding))
                .limit(k)
                .all()
            )
            
            context = "\n\n---\n\n".join([r.content for r in results])
            logger.info(
                "Búsqueda vectorial pgvector exitosa para agente %s. Retornados %d fragmentos.",
                agent_id,
                len(results),
            )
            return context

    except Exception as e:
        logger.warning(
            "No se pudo recuperar contexto vectorial para agente %s: %s",
            agent_id,
            str(e),
        )
        return ""
    finally:
        if should_close:
            db_session.close()


def update_document_content(
    db: Session, doc_id: str, filename: str, new_content: str
) -> KnowledgeDocument:
    """
    Actualiza el contenido y/o nombre de un documento de conocimiento:
    1. Recupera el documento de la base de datos SQL.
    2. Elimina los vectores antiguos de Chroma o pgvector.
    3. Segmenta el nuevo contenido en chunks.
    4. Genera nuevos embeddings e indexa en Chroma o pgvector.
    5. Actualiza el registro de SQL con el nuevo nombre, raw_content y chunk_count.
    """
    db_doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
    if not db_doc:
        raise ValueError(f"No se encontró ningún documento con el ID {doc_id}")

    agent_id = db_doc.agent_id

    # 1. Eliminar vectores antiguos de ChromaDB o pgvector
    if is_sqlite:
        collection_name = f"agent_{agent_id.replace('-', '_')}"
        try:
            collection = chroma_client.get_or_create_collection(name=collection_name)
            collection.delete(where={"document_id": doc_id})
        except Exception as e:
            logger.error(
                "Error eliminando vectores antiguos de ChromaDB para documento %s: %s",
                doc_id,
                str(e),
            )
    else:
        try:
            from models.knowledge_chunk import KnowledgeChunk
            db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc_id).delete()
        except Exception as e:
            logger.error(
                "Error eliminando vectores antiguos pgvector para documento %s: %s",
                doc_id,
                str(e),
            )

    # 2. Fragmentar el nuevo texto
    chunks = chunk_text(new_content)
    chunk_count = len(chunks)
    logger.info(
        "Documento %s actualizado y fragmentado en %d chunks.", doc_id, chunk_count
    )

    # 3. Generar embeddings e indexar si hay chunks
    if chunk_count > 0:
        try:
            embeddings = get_embeddings(chunks, task_type="retrieval_document")
            
            if is_sqlite:
                collection_name = f"agent_{agent_id.replace('-', '_')}"
                collection = chroma_client.get_or_create_collection(name=collection_name)
                ids = [f"{db_doc.id}_{i}" for i in range(chunk_count)]
                metadatas = [
                    {
                        "document_id": db_doc.id,
                        "agent_id": agent_id,
                        "chunk_index": i,
                        "filename": filename,
                    }
                    for i in range(chunk_count)
                ]

                collection.add(
                    ids=ids,
                    documents=chunks,
                    embeddings=embeddings,
                    metadatas=metadatas,
                )
                logger.info(
                    "Indexados %d nuevos vectores para documento %s en ChromaDB.",
                    chunk_count,
                    doc_id,
                )
            else:
                from models.knowledge_chunk import KnowledgeChunk
                
                for i, chunk_text_content in enumerate(chunks):
                    chunk_embedding = embeddings[i]
                    db_chunk = KnowledgeChunk(
                        document_id=db_doc.id,
                        agent_id=agent_id,
                        chunk_index=i,
                        content=chunk_text_content,
                        embedding=chunk_embedding
                    )
                    db.add(db_chunk)
                logger.info(
                    "Indexados %d nuevos vectores para documento %s en pgvector.",
                    chunk_count,
                    doc_id,
                )
        except Exception as e:
            logger.error("Error al indexar nuevos chunks: %s", str(e), exc_info=True)
            raise RuntimeError(f"Error indexando en base vectorial: {str(e)}")

    # 4. Actualizar registro SQL
    db_doc.filename = filename
    db_doc.raw_content = new_content
    db_doc.chunk_count = chunk_count
    
    db.commit()
    db.refresh(db_doc)
    return db_doc


# ── RAG por tenant (genia-agent-platform, Tareas 6.2 y 6.3) ──────────
# Extension de la recuperacion para aislar el conocimiento por tenant usando
# una coleccion por tenant en ChromaDB (`tenant_{id}`) o el filtro
# `tenant_id` en pgvector. Si el tenant no tiene Knowledge_Base, se devuelve
# contexto vacio para que el agente responda solo con prompt + modelo (3.5).

def tenant_collection_name(tenant_id: str) -> str:
    """Devuelve el nombre de la coleccion ChromaDB del tenant (`tenant_{id}`)."""
    return f"tenant_{tenant_id.replace('-', '_')}"


def retrieve_context_for_tenant(
    tenant_id: str, query: str, k: int = 4, db: Session = None
) -> str:
    """
    Recupera contexto RAG acotado exclusivamente a un tenant (Requisito 3.3).

    Usa la coleccion por tenant en ChromaDB (`tenant_{id}`) filtrando ademas por
    el metadato `tenant_id`, o el filtro `KnowledgeChunk.tenant_id` en pgvector.
    Si el tenant no tiene Knowledge_Base (coleccion inexistente o sin chunks),
    devuelve cadena vacia para que el agente responda solo con prompt + modelo
    (Requisito 3.5).

    Args:
        tenant_id: Identificador del tenant cuyo conocimiento se recupera.
        query: Consulta del usuario.
        k: Cantidad de fragmentos a recuperar.
        db: Sesion opcional de base de datos (necesaria para pgvector).

    Returns:
        Texto concatenado con los fragmentos relevantes del tenant, o "".
    """
    if not tenant_id or not query or not query.strip():
        return ""

    db_session = db
    should_close = False
    if db_session is None:
        from database import SessionLocal
        db_session = SessionLocal()
        should_close = True

    try:
        if is_sqlite:
            collection_name = tenant_collection_name(tenant_id)
            try:
                collection = chroma_client.get_collection(name=collection_name)
            except Exception:
                # Tenant sin Knowledge_Base: responder solo con prompt + modelo.
                logger.info(
                    "Tenant %s sin coleccion de conocimiento. Contexto vacio.",
                    tenant_id,
                )
                return ""

            query_embedding = get_embedding(query, task_type="retrieval_query")
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where={"tenant_id": tenant_id},
            )
            documents = results.get("documents", [[]])[0]
            documents = [doc for doc in documents if isinstance(doc, str)]
            if not documents:
                return ""
            context = "\n\n---\n\n".join(documents)
            logger.info(
                "RAG por tenant %s: %d fragmentos recuperados.",
                tenant_id,
                len(documents),
            )
            return context
        else:
            from models.knowledge_chunk import KnowledgeChunk

            query_embedding = get_embedding(query, task_type="retrieval_query")
            results = (
                db_session.query(KnowledgeChunk)
                .filter(KnowledgeChunk.tenant_id == tenant_id)
                .order_by(KnowledgeChunk.embedding.cosine_distance(query_embedding))
                .limit(k)
                .all()
            )
            if not results:
                return ""
            context = "\n\n---\n\n".join([r.content for r in results])
            logger.info(
                "RAG por tenant %s (pgvector): %d fragmentos recuperados.",
                tenant_id,
                len(results),
            )
            return context

    except Exception as e:
        logger.warning(
            "No se pudo recuperar contexto RAG para tenant %s: %s",
            tenant_id,
            str(e),
        )
        return ""
    finally:
        if should_close:
            db_session.close()


def has_knowledge_base(tenant_id: str, db: Session = None) -> bool:
    """
    Indica si un tenant tiene Knowledge_Base con al menos un documento.

    Args:
        tenant_id: Identificador del tenant.
        db: Sesion opcional de base de datos.

    Returns:
        True si existe al menos un `KnowledgeDocument` del tenant.
    """
    if not tenant_id:
        return False
    db_session = db
    should_close = False
    if db_session is None:
        from database import SessionLocal
        db_session = SessionLocal()
        should_close = True
    try:
        count = (
            db_session.query(KnowledgeDocument)
            .filter(KnowledgeDocument.tenant_id == tenant_id)
            .count()
        )
        return count > 0
    finally:
        if should_close:
            db_session.close()


def ensure_collection(db: Session, tenant_id: str, collection_name: str | None = None) -> str:
    """
    Asegura (idempotente) la coleccion ChromaDB del tenant para el RAG.

    Crea (o recupera si ya existe) la coleccion por tenant `tenant_{id}` en
    ChromaDB. Es idempotente: re-ejecutar no duplica la coleccion. En entornos
    sin ChromaDB local (pgvector) no hay coleccion fisica que crear y la funcion
    simplemente devuelve el nombre logico de la coleccion del tenant.

    Args:
        db: Sesion de base de datos (no usada en ChromaDB; presente por simetria).
        tenant_id: Identificador del tenant.
        collection_name: Nombre explicito de coleccion; por defecto `tenant_{id}`.

    Returns:
        El nombre de la coleccion asegurada para el tenant.
    """
    name = collection_name or tenant_collection_name(tenant_id)
    if is_sqlite and chroma_client is not None:
        try:
            chroma_client.get_or_create_collection(name=name)
            logger.info("Coleccion ChromaDB asegurada para tenant %s (%s)", tenant_id, name)
        except Exception as exc:  # noqa: BLE001 - best-effort en provisioning
            logger.warning(
                "No se pudo asegurar la coleccion ChromaDB '%s' del tenant %s: %s",
                name,
                tenant_id,
                exc,
            )
    else:
        logger.info(
            "Vector store pgvector: la coleccion logica del tenant %s es '%s' "
            "(filtro por tenant_id).",
            tenant_id,
            name,
        )
    return name
