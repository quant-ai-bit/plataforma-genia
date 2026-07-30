"""
Script de creación e inicialización del Agente "Juan" para "A la mesa Juan cocina"
(Venta de Ají Artesanal en Pereira, Colombia).

Crea el agente en la base de datos de PRODUCCIÓN (Supabase PostgreSQL) y LOCAL (SQLite)
con su System Prompt refinado, campos personalizados de perfilamiento CRM y 3 documentos de base de conocimiento.
"""

import sys
import os

# Agregar directorio backend al path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from database import SessionLocal
from models.agent import Agent
from models.knowledge import KnowledgeDocument

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_DB_URL = "postgresql://postgres.ppzsnsovdmxwofmuppfv:platagenia2026@aws-1-us-west-2.pooler.supabase.com:6543/postgres"

# ── 1. Definición del System Prompt ──────────────────────────────────────
JUAN_SYSTEM_PROMPT = """Eres "Juan", el asistente virtual de atención al cliente y ventas de "A la mesa Juan cocina", un emprendimiento artesanal gastronómico ubicado en Pereira, Colombia, especializado en la elaboración y venta de Ají Artesanal en frasco.

TU IDIOMA DE TRABAJO:
- Debes responder SIEMPRE en español corporativo, cercano, cálido y profesional colombiano (trato respetuoso de "tú" o "usted" según el cliente).
- NUNCA respondas en inglés.

TU OBJETIVO PRINCIPAL:
Tu interacción será exclusivamente a través de chat (Web y WhatsApp). Tu enfoque es consultivo y comercial: tu labor es asesorar al cliente sobre nuestro Ají Artesanal, resolver sus inquietudes con precisión absoluta, perfilando su pedido paso a paso y guiándolo para concretar la compra de sus frascos con entrega a domicilio en Pereira.

## INSTRUCCIONES DE CAPTURA DE LEADS (save_lead_info):
A medida que el cliente te brinde sus datos o cuando completes el embudo de pedido (Pasos 1 a 6), DEBES invocar la herramienta 'save_lead_info' de forma incremental con los siguientes campos:
- nombre: Nombre completo del cliente.
- telefono: Teléfono de contacto / WhatsApp.
- cantidad_frascos: Cantidad de frascos de 240 ml deseados (ej: "1 frasco", "2 frascos", "$25.000 c/u").
- direccion_entrega: Dirección detallada de entrega en Pereira.
- barrio_ciudad: Barrio o sector de Pereira.
- metodo_pago: Método de pago preferido ("Nequi", "Daviplata", "Bancolombia", "Efectivo contra entrega").
- notas_pedido: Indicaciones especiales para la entrega.

TONO Y PERSONALIDAD:
- Eres formal, educado, ejecutivo, pero sumamente cálido, apetitoso y atento.
- ESTRICTAMENTE PROHIBIDO usar diminutivos (ejemplo: NO digas "ajisito", "frasquito", "momentico", "pedidito").
- ESTRICTAMENTE PROHIBIDO usar apodos informales o excesos de confianza (ejemplo: NO digas "amigo", "jefe", "parce", "míster", "lindo"). Llama al cliente por su nombre una vez lo conozcas.
- NUNCA uses la palabra "arrendamiento" o términos fuera del contexto gastronómico. Habla de "pedido", "frascos", "entrega a domicilio", "elaboración artesanal".

REGLAS DE OPERACIÓN Y GUARDARRAÍLES (CRÍTICO):
1. ERES 100% DETERMINISTA Y VERAZ: NO inventes sabores, precios, presentaciones ni condiciones de envío que no estén en tu base de conocimiento.
2. NO estás autorizado para ofrecer ni negociar descuentos de ningún tipo. El precio es fijo: $25.000 COP por frasco de 240 ml.
3. REGLA DE DOMICILIO Y ENTREGAS EN PEREIRA: Si la entrega es en la ciudad de Pereira, el domicilio NO TIENE RECARGO (es GRATIS), ya que los pedidos se consolidan en una sola salida de entrega por ruta.
4. REGLA DE REFRIGERACIÓN Y CONSERVACIÓN: Debes informar o recordar que al ser un producto 100% libre de conservantes y aditivos artificiales, DEBE mantenerse refrigerado y consumirse preferiblemente dentro de los 45 días posteriores a su apertura.
5. REGLA DE UNA SOLA PREGUNTA A LA VEZ (CRÍTICO): DEBES hacer ÚNICAMENTE UNA PREGUNTA por mensaje. Queda TOTALMENTE PROHIBIDO enviar 2 o más preguntas en un solo mensaje. Espera la respuesta del cliente antes de avanzar al siguiente paso del embudo.
6. Cero tolerancia a faltas de respeto o lenguaje vulgar. Si el cliente es irrespetuoso, infórmale amablemente que transferirás la conversación al equipo humano.
7. REGLA DE EJECUCIÓN INVISIBLE DE HERRAMIENTAS: NUNCA escribas fragmentos de código, comandos 'tool_code' ni sentencias 'print(...)' dentro de tu respuesta visible. Ejecuta las herramientas de forma interna y entrega únicamente la respuesta final limpia en español.

PROCESO DE ATENCIÓN Y EMBUDO DE PEDIDO (FUNNEL):
Haz las siguientes preguntas de perfilamiento ESTRICTAMENTE UNA POR UNA. Espera la respuesta del usuario antes de pasar a la siguiente:
1. Nombre del cliente con quien conversas.
2. ¿Cuántos frascos de Ají Artesanal (240 ml - $25.000 c/u) deseas pedir?
3. ¿En qué dirección y barrio de Pereira te entregamos tu pedido?
4. ¿Prefieres realizar el pago por transferencia electrónica (Nequi / Daviplata / Bancolombia) o en efectivo contra entrega?
5. Confirmación final de los detalles del pedido (cantidad, total en COP, dirección y método de pago) y agendamiento para la ruta de entrega.

INSTRUCCIONES PARA TRANSFERENCIA A AGENTE HUMANO (trigger_human_handoff):
Debes invocar la herramienta 'trigger_human_handoff' en los siguientes casos:
1. Cuando el cliente solicite explícitamente hablar con una persona o asesor humano.
2. Cuando el cliente tenga solicitudes especiales fuera de la ciudad de Pereira o compras al por mayor / institucionales.
3. Cuando el pedido quede totalmente confirmado para que el equipo de cocina y despacho procese la entrega.

MENSAJE ANTES DE TRANSFERIR:
"¡Excelente! He registrado todos los detalles de tu pedido. Voy a transferir tu chat con nuestro equipo de entregas de 'A la mesa Juan cocina' para confirmar el despacho de tus frascos. ¡Muchas gracias por tu compra!"
"""

# ── 2. Campos Personalizados de Perfilamiento CRM ───────────────────────
JUAN_CUSTOM_FIELDS = [
    {"key": "nombre", "label": "Nombre del Cliente", "type": "text", "required": True},
    {"key": "telefono", "label": "Teléfono / WhatsApp", "type": "text", "required": True},
    {"key": "cantidad_frascos", "label": "Cantidad de Frascos (240ml)", "type": "text", "required": True},
    {"key": "direccion_entrega", "label": "Dirección de Entrega", "type": "text", "required": True},
    {"key": "barrio_ciudad", "label": "Barrio / Municipio", "type": "text", "required": False},
    {"key": "metodo_pago", "label": "Método de Pago", "type": "select", "required": False, "options": ["Nequi", "Daviplata", "Bancolombia", "Efectivo contra entrega"]},
    {"key": "notas_pedido", "label": "Notas de Entrega", "type": "text", "required": False}
]

# ── 3. Documentos de Base de Conocimiento ──────────────────────────────
KB_DOCUMENTS = [
    {
        "filename": "aji_artesanal_producto.txt",
        "content": """PRODUCTO: NUEVO AJÍ ARTESANAL MIX DE 7 VARIEDADES DE CHILES
Marca / Negocio: A la mesa Juan cocina
Ubicación: Pereira, Risaralda, Colombia

DESCRIPCIÓN Y COMPOSICIÓN:
- Elaborado con una cuidadosa mezcla artesanal de 7 variedades de chiles mexicanos deshidratados:
  1. Mulato
  2. Morita
  3. Chipotle
  4. Guajillo
  5. Pasilla
  6. Ancho
  7. Chile de la Tierra
- Complementados con Chile Criollo fresco de cultivo propio, artesanal y orgánico.
- Receta que logra el equilibrio perfecto entre sabor, aroma y un picante moderado-alto delicioso.
- Acompañante ideal para carnes, empanadas, sancocho, sopas, tacos, pastas, huevos, asados y cualquier tipo de alimento.

CARACTERÍSTICAS Y PRESENTACIÓN:
- 100% Artesanal y natural.
- Sin conservantes ni aditivos artificiales.
- Presentación: Envase / Frasco de vidrio de 240 ml.
- Precio: $25.000 COP por frasco.

REFRIGERACIÓN Y CONSERVACIÓN:
- Al ser un producto libre de conservantes artificiales, DEBE mantenerse refrigerado (en la nevera) inmediatamente.
- Consumirse preferiblemente dentro de los 45 días posteriores a su apertura.
"""
    },
    {
        "filename": "envios_y_domicilios_pereira.txt",
        "content": """POLÍTICA DE ENVÍOS Y DOMICILIOS EN PEREIRA
Negocio: A la mesa Juan cocina

COBERTURA Y TARIFAS DE DOMICILIO:
- En la ciudad de Pereira: El domicilio NO tiene recargo (es GRATIS).
- Razón: Los pedidos se recogen y consolidan para salir en una sola ruta de entregas directas a domicilio.
- Fuera de Pereira / Municipios aledaños (Dosquebradas, Santa Rosa, etc.): Se realiza cotización o despacho especial coordinado con el equipo de ventas.

MÉTODOS DE PAGO ACEPTADOS:
1. Transferencia electrónica: Nequi, Daviplata o Bancolombia.
2. Efectivo contra entrega: Pago al repartidor en el momento de recibir los frascos en la puerta de la casa u oficina.

PROCESO DE PEDIDO:
1. El cliente proporciona su nombre, cantidad de frascos de 240 ml ($25.000 c/u), dirección de entrega en Pereira y teléfono.
2. Se confirma el total en COP y el método de pago elegido.
3. Se agenda en la ruta de despacho del día.
"""
    },
    {
        "filename": "preguntas_frecuentes_aji.txt",
        "content": """PREGUNTAS FRECUENTES (FAQ) - AJÍ ARTESANAL JUAN COCINA

1. ¿Qué tan picante es el ají?
R: Tiene un picante equilibrado y sabroso. La mezcla de los 7 chiles mexicanos deshidratados aporta sabor ahumado, aroma y sazón, mientras que el chile criollo fresco le da el toque picante perfecto sin quemar la boca.

2. ¿Requiere nevera / refrigeración?
R: Sí, totalmente. Al ser 100% artesanal y sin ningún tipo de conservantes ni aditivos químicos, debe conservarse en refrigeración y consumir dentro de 45 días tras su apertura.

3. ¿Cuánto vale el envío en Pereira?
R: Si estás en Pereira, la entrega no tiene recargo adicional porque organizamos rutas consolidadas para llevar todos los pedidos.

4. ¿Tienen presentaciones más grandes o institucionales?
R: La presentación estándar oficial es de 240 ml por $25.000 COP. Para pedidos institucionales o eventos, se transfiere la consulta con el chef/propietario.
"""
    }
]


def sync_agent_to_db(db: Session, target_name: str):
    try:
        existing_agent = db.query(Agent).filter(
            Agent.name.ilike("%Juan%"),
            Agent.description.ilike("%Juan cocina%")
        ).first()

        if not existing_agent:
            existing_agent = db.query(Agent).filter(Agent.name == "Juan").first()

        if existing_agent:
            logger.info("[%s] Actualizando agente existente Juan (ID: %s)...", target_name, existing_agent.id)
            agent = existing_agent
            agent.name = "Juan - A la mesa Juan cocina"
            agent.description = "Asistente virtual de atención al cliente y ventas de Ají Artesanal Mix de 7 Chiles en Pereira, Colombia."
            agent.system_prompt = JUAN_SYSTEM_PROMPT
            agent.provider = "vertex"
            agent.model = "gemini-2.5-flash"
            agent.temperature = 0.5
            agent.max_tokens = 2048
            agent.custom_fields = JUAN_CUSTOM_FIELDS
            agent.channels = ["web", "whatsapp"]
            agent.timezone = "America/Bogota"
            agent.user_id = "2d5fc55e-48e7-43bc-8d3e-624167bdae76"
        else:
            logger.info("[%s] Creando nuevo agente Juan - A la mesa Juan cocina...", target_name)
            agent = Agent(
                name="Juan - A la mesa Juan cocina",
                description="Asistente virtual de atención al cliente y ventas de Ají Artesanal Mix de 7 Chiles en Pereira, Colombia.",
                system_prompt=JUAN_SYSTEM_PROMPT,
                provider="vertex",
                model="gemini-2.5-flash",
                temperature=0.5,
                max_tokens=2048,
                custom_fields=JUAN_CUSTOM_FIELDS,
                channels=["web", "whatsapp"],
                notification_phone="+573209673284",
                whatsapp_provider="qr_code",
                stt_provider="groq_whisper",
                timezone="America/Bogota",
                user_id="2d5fc55e-48e7-43bc-8d3e-624167bdae76",
            )
            db.add(agent)
            db.flush()

        db.commit()
        db.refresh(agent)
        logger.info("[%s] ✅ Agente guardado exitosamente. ID: %s | Nombre: %s", target_name, agent.id, agent.name)

        # ── Cargar Documentos de Base de Conocimiento ──────────────────────
        logger.info("[%s] Cargando base de conocimiento para el agente %s...", target_name, agent.id)
        for doc in KB_DOCUMENTS:
            existing_doc = db.query(KnowledgeDocument).filter(
                KnowledgeDocument.agent_id == agent.id,
                KnowledgeDocument.filename == doc["filename"]
            ).first()

            if existing_doc:
                existing_doc.raw_content = doc["content"]
                existing_doc.chunk_count = len(doc["content"].split("\n\n"))
                logger.info("[%s]   [KB] Documento %s actualizado.", target_name, doc["filename"])
            else:
                new_doc = KnowledgeDocument(
                    agent_id=agent.id,
                    filename=doc["filename"],
                    content_type="text/plain",
                    raw_content=doc["content"],
                    chunk_count=len(doc["content"].split("\n\n")),
                )
                db.add(new_doc)
                logger.info("[%s]   [KB] Documento %s creado.", target_name, doc["filename"])

        db.commit()
        logger.info("[%s] ✅ Base de conocimiento integrada exitosamente.", target_name)
        return agent.id
    except Exception as e:
        db.rollback()
        logger.error("[%s] ❌ Error al procesar agente: %s", target_name, e, exc_info=True)
        return None


def main():
    print("="*60)
    print("INICIANDO SINCRONIZACIÓN DEL AGENTE 'JUAN' (LOCAL Y PRODUCCIÓN)")
    print("="*60)

    # 1. Base de Datos Local (SQLite)
    logger.info("--> Conectando a Base de Datos Local (SQLite)...")
    local_db = SessionLocal()
    local_id = sync_agent_to_db(local_db, "LOCAL DB (SQLite)")
    local_db.close()

    # 2. Base de Datos de Producción (Supabase PostgreSQL)
    logger.info("--> Conectando a Base de Datos de Producción (Supabase PostgreSQL)...")
    prod_engine = create_engine(SUPABASE_DB_URL, pool_pre_ping=True)
    
    # Aplicar DDL no destructivo para columnas nuevas en Supabase
    with prod_engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE agents ADD COLUMN IF NOT EXISTS diagnostic_business_context JSON;"))
            conn.execute(text("ALTER TABLE agents ADD COLUMN IF NOT EXISTS diagnostic_last_run_at TIMESTAMP WITH TIME ZONE;"))
            conn.execute(text("ALTER TABLE agents ADD COLUMN IF NOT EXISTS diagnostic_status VARCHAR(50);"))
            conn.commit()
            logger.info("--> [Supabase] Columnas de diagnóstico verificadas/agregadas correctamente.")
        except Exception as ex_ddl:
            logger.warning("--> [Supabase] Nota en DDL de columnas de diagnóstico: %s", ex_ddl)

    ProdSession = sessionmaker(bind=prod_engine)
    prod_db = ProdSession()
    prod_id = sync_agent_to_db(prod_db, "PROD DB (Supabase)")
    prod_db.close()

    print("\n" + "="*60)
    print("RESULTADO DE SINCRONIZACION:")
    print(f" - Local DB Agent ID: {local_id}")
    print(f" - Prod DB Agent ID:  {prod_id}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
