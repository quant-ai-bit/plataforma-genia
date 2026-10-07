"""
Script para la creación directa del agente 'Luna' (Dr. Jorge Eduardo Giraldo Salazar)
en la PLATAFORMA GENIA (Base de datos Supabase PostgreSQL y SQLite local).
"""

import json
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models.agent import Agent
from models.knowledge import KnowledgeDocument
from services.knowledge_service import process_and_index_document

PROD_DB_URL = "postgresql://postgres.ppzsnsovdmxwofmuppfv:platagenia2026@aws-1-us-west-2.pooler.supabase.com:6543/postgres"
LOCAL_DB_URL = "sqlite:///./data/genia.db"

SYSTEM_PROMPT = """ROL E IDENTIDAD DEL AGENTE:
Eres Luna, la asistente virtual oficial del Dr. Jorge Eduardo Giraldo Salazar, médico general con amplia trayectoria en consulta externa, hospitalización, urgencias médicas, y atención tanto pediátrica (niños) como de adultos y medicina geriátrica (adulto mayor).

MISIÓN Y OBJETIVO:
Atender a los pacientes que se comunican vía chat (WhatsApp o web) con calidez, empatía y alto estándar profesional. Tu meta principal es resolver dudas administrativas sobre los servicios médicos del doctor, realizar un triaje orientativo no invasivo, recopilar los datos esenciales del paciente (lead) y coordinar el agendamiento de citas en dos modalidades:
1. Teleconsulta: Atención médica virtual por videollamada para pacientes en Pereira, Colombia o cualquier lugar del mundo.
2. Consulta Domiciliaria: Atención médica presencial en el hogar del paciente, con cobertura exclusiva en Pereira, Dosquebradas y Santa Rosa de Cabal (Risaralda).

IDENTIDAD Y TONO:
- Nombre: Luna.
- Identidad: Eres un asistente virtual impulsado por inteligencia artificial. Si te preguntan si eres humana o el doctor, responde con total transparencia y cortesía que eres Luna, la asistente virtual del Dr. Jorge Eduardo Giraldo Salazar.
- Tono: Mixto (cálido, cercano, empático y respetuoso). Quien te escribe suele estar enfermo o preocupado; utiliza un lenguaje acogedor y humano, sin caer en formalismos excesivamente rígidos ("cuadriculados") ni en informalidades inapropiadas.
- Estilo: Respuestas claras, directas, breves y comprensibles. No envíes párrafos extensos ni abrumes con múltiples preguntas a la vez.

POLÍTICA DE SEGURIDAD CLÍNICA Y LÍMITES ÉTICOS (ESTRICTO):
1. PROHIBICIÓN TOTAL DE DIAGNOSTICAR: Nunca digas "usted padece de...", "su diagnóstico es..." ni interpretes de forma concluyente síntomas o exámenes de laboratorio. El diagnóstico definitivo solo lo realiza el Dr. Jorge Eduardo durante la consulta formal.
2. PROHIBICIÓN TOTAL DE FORMULAR O MEDICAR: Nunca recetes fármacos, indiques dosis, ni sugieras automedicación.
3. DETECCIÓN DE EMERGENCIAS VITALES (TRIAJE ROJO):
   Si el paciente describe síntomas de alarma como dolor torácico opresivo fuerte, asfixia/dificultad respiratoria severa, pérdida de conciencia, convulsiones activas o sangrado profuso que no cede:
   RESPONDE INMEDIATAMENTE:
   "Estimado/a [Nombre], por los síntomas que describes, esto podría tratarse de una emergencia médica que requiere atención hospitalaria urgente e inmediata. Por favor dirígete de inmediato al centro de urgencias o clínica más cercana, o llama a la línea de emergencias nacional 123 (en Colombia). La salud es lo primero; no esperes a una cita programada."

POLÍTICA DE TARIFAS Y SERVICIOS:
- Teleconsulta Estándar: Tarifa fija oficial.
- Teleconsulta Prioritaria Nocturna (después de las 8:00 p.m.): Aplica tarifa con sobrecosto por disponibilidad en horario especial.
- Consulta Domiciliaria: Rango de tarifa según ubicación geográfica (Pereira, Dosquebradas o Santa Rosa de Cabal).
- Regla de Precios: No estás autorizada bajo ninguna circunstancia a negociar precios, otorgar descuentos o modificar los valores establecidos por el doctor.

FLUJO CONVERSACIONAL PASO A PASO:
1. Saludo cordial y bienvenida a la consulta del Dr. Jorge Eduardo Giraldo Salazar.
2. Identificación del servicio: ¿Teleconsulta virtual o Consulta médica domiciliaria? (Si piden domiciliaria fuera de Pereira/Dosquebradas/Santa Rosa, aclara que solo aplica en esos municipios pero que pueden tomar teleconsulta).
3. Captura orgánica de datos (uno a uno):
   - Nombre completo del paciente (o acudiente).
   - Edad del paciente (clasifica si es niño, adulto o adulto mayor).
   - Municipio y dirección exacta (si es para domicilio).
   - Motivo de consulta o síntomas principales.
   - Antecedentes clave (enfermedades de base o alergias relevantes).
4. Agendamiento:
   - Ofrece el primer espacio disponible en la agenda del doctor.
   - Si no le sirve, brinda alternativas disponibles.
5. Transferencia a Humano: Si el paciente solicita hablar con una persona:
   "Comprendo perfectamente. Te transfiero en este momento con la asistente del Dr. Giraldo para que te brinde una atención personalizada. Por favor ten un poco de paciencia mientras revisamos la conversación en la plataforma y te respondemos. ¡Estamos atentos!"
"""

KB_TEXT = """# BASE DE CONOCIMIENTO - DR. JORGE EDUARDO GIRALDO SALAZAR

1. INFORMACIÓN PROFESIONAL DEL DOCTOR
Nombre: Dr. Jorge Eduardo Giraldo Salazar
Profesión: Médico General
Áreas de experiencia y competencia:
- Consulta médica externa (atención ambulatoria, controles y valoración general).
- Hospitalización y manejo de pacientes internados.
- Urgencias médicas generales y triaje clínico.
- Pediatría (atención integral a recién nacidos, niños y adolescentes).
- Medicina del adulto y adulto mayor (geriatría y manejo de enfermedades crónicas no transmisibles).
Enfoque de atención: Trato humano, diagnóstico preventivo y acompañamiento personalizado con criterio ético y científico.

2. SERVICIOS Y MODALIDADES DE ATENCIÓN

A. Teleconsulta Médica General
Descripción: Consulta médica integral realizada mediante videollamada interactiva segura.
Cobertura geográfica: Ilimitada (pacientes ubicados en Pereira, resto de Colombia o en el exterior).
Horarios:
- Franja ordinaria: Lunes a viernes en horarios diurnos y vespertinos.
- Franja prioritaria/nocturna: A partir de las 8:00 p.m. para motivos que requieran atención médica oportuna fuera del horario laboral estándar.
Requisitos técnicos: Dispositivo con conexión estable a internet, cámara y micrófono activos.
Documentos emitidos:
- Fórmula médica digital formal firmada con registro médico.
- Órdenes médicas para exámenes de laboratorio o imágenes diagnósticas si se requieren.
- Certificados médicos o recomendaciones clínicas.

B. Consulta Médica Domiciliaria
Descripción: Atención médica presencial directamente en el hogar del paciente.
Zonas de cobertura exclusiva:
1. Pereira (casco urbano y sectores aledaños concertados).
2. Dosquebradas (Risaralda).
3. Santa Rosa de Cabal (Risaralda).
Beneficios: Pacientes con movilidad reducida, adultos mayores, pacientes postquirúrgicos, niños pequeños que prefieren evitar salas de espera, o personas con poco tiempo disponible.
Logística: Tiempos de desplazamiento programados entre consulta y consulta (mínimo 30-45 minutos) para garantizar puntualidad.

3. TARIFAS Y POLÍTICAS DE PAGO
Estructura tarifaria:
- Teleconsulta médica ordinaria: Tarifa estándar.
- Teleconsulta médica nocturna / prioritaria (después de las 8:00 p.m.): Tarifa con sobrecosto por nocturnidad y atención inmediata.
- Consulta domiciliaria: Tarifa escalonada por zona geográfica (Pereira / Dosquebradas / Santa Rosa de Cabal).
Políticas financieras:
- Tarifas fijas, no sujetas a descuentos comerciales.
- Métodos de pago: Transferencia bancaria, Nequi, Daviplata o efectivo en la visita domiciliaria.

4. PREGUNTAS FRECUENTES (FAQ)
- Atención a niños: El Dr. Jorge Eduardo cuenta con amplia experiencia en consulta y urgencias pediátricas.
- Solicitud para terceros: Un familiar o acudiente puede gestionar la cita indicando datos del paciente.
- Incapacidad médica: El médico está legalmente facultado para expedir incapacidad laboral o escolar si el criterio clínico lo amerita.
- Cancelaciones: Se puede reprogramar o cancelar con mínimo 2 horas de anticipación.
- Urgencias vitales: En caso de paro, dolor torácico severo, asfixia, pérdida de conciencia o sangrado profuso, acudir de inmediato al hospital más cercano o llamar al 123.
"""

CUSTOM_FIELDS = [
    {
        "name": "nombre_paciente",
        "label": "Nombre del Paciente",
        "type": "text",
        "required": True,
        "description": "Nombre completo del paciente o acudiente"
    },
    {
        "name": "telefono_contacto",
        "label": "Teléfono / WhatsApp",
        "type": "text",
        "required": True,
        "description": "Número de teléfono para confirmación y recordatorios"
    },
    {
        "name": "edad_paciente",
        "label": "Edad del Paciente",
        "type": "text",
        "required": True,
        "description": "Edad para determinar atención pediátrica, adulto o adulto mayor"
    },
    {
        "name": "tipo_consulta",
        "label": "Tipo de Consulta",
        "type": "text",
        "required": True,
        "description": "Teleconsulta virtual vs Consulta Médica Domiciliaria"
    },
    {
        "name": "direccion_municipio",
        "label": "Ubicación / Dirección",
        "type": "text",
        "required": False,
        "description": "Municipio (Pereira, Dosquebradas, Santa Rosa) y dirección para domicilios"
    },
    {
        "name": "motivo_consulta",
        "label": "Motivo de Consulta",
        "type": "text",
        "required": True,
        "description": "Síntomas principales o motivo de atención"
    },
    {
        "name": "antecedentes_alergias",
        "label": "Antecedentes y Alergias",
        "type": "text",
        "required": False,
        "description": "Enfermedades preexistentes relevantes o alergias"
    }
]

def create_agent_in_db(db_url: str, db_name: str, agent_id: str):
    print(f"\n--- Creando agente en {db_name} ---")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        user_id = "2d5fc55e-48e7-43bc-8d3e-624167bdae76"  # Alejandro Baena (Admin)

        # Verificar si ya existe
        existing = db.query(Agent).filter(Agent.name == "Luna").first()
        if existing:
            print(f"[*] El agente Luna ya existía con ID: {existing.id}. Actualizando datos...")
            existing.system_prompt = SYSTEM_PROMPT
            existing.description = "Asistente virtual de agendamiento y atención médica inicial del Dr. Jorge Eduardo Giraldo Salazar (Teleconsulta y Visitas Domiciliarias)"
            existing.custom_fields = CUSTOM_FIELDS
            existing.provider = "vertex"
            existing.model = "gemini-2.5-flash"
            existing.temperature = 0.3
            existing.max_tokens = 1024
            existing.status = "active"
            existing.channels = ["web", "whatsapp"]
            existing.timezone = "America/Bogota"
            db.commit()
            target_agent = existing
        else:
            target_agent = Agent(
                id=agent_id,
                user_id=user_id,
                name="Luna",
                description="Asistente virtual de agendamiento y atención médica inicial del Dr. Jorge Eduardo Giraldo Salazar (Teleconsulta y Visitas Domiciliarias)",
                system_prompt=SYSTEM_PROMPT,
                provider="vertex",
                model="gemini-2.5-flash",
                temperature=0.3,
                max_tokens=1024,
                status="active",
                channels=["web", "whatsapp"],
                notification_phone=None,
                custom_fields=CUSTOM_FIELDS,
                timezone="America/Bogota"
            )
            db.add(target_agent)
            db.commit()
            db.refresh(target_agent)
            print(f"[+] Agente Luna creado exitosamente con ID: {target_agent.id}")

        print(f"    Nombre: {target_agent.name}")
        print(f"    Proveedor: {target_agent.provider} | Modelo: {target_agent.model}")
        print(f"    Campos de Leads: {len(target_agent.custom_fields)} configurados")

        # Indexar Base de Conocimientos
        print("[*] Indexando Base de Conocimiento médica...")
        kb_bytes = KB_TEXT.encode("utf-8")
        try:
            doc = process_and_index_document(
                db=db,
                agent_id=target_agent.id,
                filename="Base_Conocimiento_Dr_Jorge_Eduardo_Giraldo.txt",
                content_type="text/plain",
                file_bytes=kb_bytes
            )
            print(f"[+] Base de conocimiento indexada con éxito:")
            print(f"    Doc ID: {doc.id}")
            print(f"    Chunks: {doc.chunk_count}")
        except Exception as ke:
            print(f"[!] Nota sobre embeddings/RAG: {ke}")

        return target_agent.id
    except Exception as e:
        print(f"[-] Error en {db_name}: {e}")
        db.rollback()
        raise e
    finally:
        db.close()

def main():
    agent_uuid = uuid.uuid4().hex
    print("==================================================")
    print(" INICIANDO CREACIÓN DIRECTA DE AGENTE LUNA")
    print(" PLATAFORMA GENIA")
    print("==================================================")

    # 1. Crear en Supabase Producción
    prod_agent_id = create_agent_in_db(PROD_DB_URL, "Supabase Postgres (Producción)", agent_uuid)

    # 2. Crear en SQLite Local si existe
    if os.path.exists("./data/genia.db"):
        try:
            create_agent_in_db(LOCAL_DB_URL, "SQLite Local (Desarrollo)", prod_agent_id)
        except Exception as le:
            print(f"[!] Aviso en SQLite local: {le}")

    print("\n==================================================")
    print(" AGENTE LUNA CREADO Y ACTIVO EN PLATAFORMA GENIA")
    print(f" ID DEL AGENTE: {prod_agent_id}")
    print(f" URL DEMO WEB DIRECTA: https://genia.com.co/agents/{prod_agent_id}")
    print("==================================================")

if __name__ == "__main__":
    main()
