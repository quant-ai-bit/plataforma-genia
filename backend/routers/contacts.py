"""
Router de Contactos Precargados para PLATAFORMA GENIA.

Permite a los usuarios cargar masivamente bases de datos de clientes (CSV/Excel)
para sus agentes, asociándolas estrictamente al agent_id de forma privada.
"""

import csv
import io
import logging
import re
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from database import get_db
from models.agent import Agent
from models.contact import PreloadedContact
from schemas.contact import PreloadedContactResponse
from services.auth_service import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["Contacts"])


def _normalize_phone(raw_phone: str) -> str:
    """Limpia caracteres no numéricos dejando el número base para búsquedas."""
    if not raw_phone:
        return ""
    digits = re.sub(r"\D", "", str(raw_phone))
    return digits


@router.post("/{agent_id}/contacts/upload")
async def upload_agent_contacts(
    agent_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Carga masivamente una base de datos de contactos (CSV o Excel) para un agente específico.
    Guarda los registros asociados de forma aislada a `agent_id`.
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agente {agent_id} no encontrado.",
        )

    filename = file.filename or ""
    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo subido está vacío.",
        )

    parsed_rows = []

    # 1. Intentar procesar como XLSX si es .xlsx / .xls
    if filename.lower().endswith((".xlsx", ".xls")):
        try:
            import openpyxl
            workbook = openpyxl.load_workbook(filename=io.BytesIO(contents), data_only=True)
            sheet = workbook.active
            rows = list(sheet.iter_rows(values_only=True))
            if rows:
                headers = [str(h or "").strip().lower() for h in rows[0]]
                for r in rows[1:]:
                    if not r or not any(r):
                        continue
                    row_dict = {}
                    for idx, val in enumerate(r):
                        if idx < len(headers):
                            row_dict[headers[idx]] = str(val or "").strip()
                    parsed_rows.append(row_dict)
        except Exception as ex_excel:
            logger.warning(f"[CONTACTS UPLOAD] Falló lectura XLSX nativa, intentando parsear como texto CSV: {ex_excel}")

    # 2. Si no es XLSX o falló, procesar como CSV (con fallback de codificación)
    if not parsed_rows:
        text_content = ""
        for encoding in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
            try:
                text_content = contents.decode(encoding)
                break
            except Exception:
                continue

        if not text_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo decodificar el archivo CSV con formatos UTF-8 o Latin-1.",
            )

        # Detectar delimitador (, o ;)
        sample = text_content[:2000]
        delimiter = ";" if sample.count(";") > sample.count(",") else ","

        reader = csv.DictReader(io.StringIO(text_content), delimiter=delimiter)
        for row in reader:
            clean_row = {str(k or "").strip().lower(): str(v or "").strip() for k, v in row.items()}
            parsed_rows.append(clean_row)

    if not parsed_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se encontraron filas de datos en el archivo subido.",
        )

    # 3. Mapear campos (Nombre, Teléfono, Email, Notas, Custom Data)
    imported_count = 0
    updated_count = 0

    for row in parsed_rows:
        # Detectar columna de nombre
        name = row.get("nombre") or row.get("name") or row.get("cliente") or row.get("contacto") or ""
        # Detectar columna de teléfono
        phone = (
            row.get("telefono")
            or row.get("teléfono")
            or row.get("phone")
            or row.get("celular")
            or row.get("whatsapp")
            or row.get("numero")
            or row.get("número")
            or ""
        )
        # Detectar correo
        email = row.get("email") or row.get("correo") or row.get("mail") or None
        notes = row.get("notas") or row.get("notes") or row.get("observaciones") or None

        if not name or not phone:
            continue

        clean_phone = _normalize_phone(phone)
        if not clean_phone:
            continue

        # Recopilar todo lo demás en custom_data
        known_keys = {"nombre", "name", "cliente", "contacto", "telefono", "teléfono", "phone", "celular", "whatsapp", "numero", "número", "email", "correo", "mail", "notas", "notes", "observaciones"}
        custom_data = {k: v for k, v in row.items() if k not in known_keys and v}

        # Verificar si ya existe este contacto para el agente por teléfono
        existing = (
            db.query(PreloadedContact)
            .filter(
                PreloadedContact.agent_id == agent_id,
                PreloadedContact.phone == clean_phone,
            )
            .first()
        )

        if existing:
            existing.name = name
            if email:
                existing.email = email
            if notes:
                existing.notes = notes
            if custom_data:
                current_custom = existing.custom_data or {}
                current_custom.update(custom_data)
                existing.custom_data = current_custom
            updated_count += 1
        else:
            new_contact = PreloadedContact(
                agent_id=agent_id,
                name=name,
                phone=clean_phone,
                email=email,
                notes=notes,
                custom_data=custom_data if custom_data else None,
            )
            db.add(new_contact)
            imported_count += 1

    db.commit()
    logger.info(
        "[CONTACTS UPLOAD] Agente %s: %d creados, %d actualizados desde archivo %s",
        agent_id,
        imported_count,
        updated_count,
        filename,
    )

    return {
        "status": "success",
        "message": f"Base de datos procesada correctamente: {imported_count} contactos creados, {updated_count} actualizados.",
        "created": imported_count,
        "updated": updated_count,
    }


@router.get("/{agent_id}/contacts", response_model=List[PreloadedContactResponse])
def list_agent_contacts(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Lista todos los contactos precargados pertenecientes exclusivamente a un agente."""
    contacts = (
        db.query(PreloadedContact)
        .filter(PreloadedContact.agent_id == agent_id)
        .order_by(PreloadedContact.created_at.desc())
        .all()
    )
    return contacts


@router.delete("/{agent_id}/contacts/{contact_id}", status_code=status.HTTP_200_OK)
def delete_agent_contact(
    agent_id: str,
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Elimina un contacto precargado de la base privada del agente."""
    contact = (
        db.query(PreloadedContact)
        .filter(
            PreloadedContact.id == contact_id,
            PreloadedContact.agent_id == agent_id,
        )
        .first()
    )

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contacto no encontrado.",
        )

    db.delete(contact)
    db.commit()
    return {"status": "success", "message": "Contacto eliminado exitosamente."}
