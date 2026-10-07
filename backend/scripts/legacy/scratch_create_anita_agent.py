import json
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.agent import Agent
from models.knowledge import KnowledgeDocument
from services.knowledge_service import process_and_index_document

DATABASE_URL = "postgresql://postgres.ppzsnsovdmxwofmuppfv:platagenia2026@aws-1-us-west-2.pooler.supabase.com:6543/postgres"

system_prompt = """ROL E IDENTIDAD DEL AGENTE:
Eres Anita Gourmet, el asistente virtual de atención al cliente de "Ana María Gourmet", un prestigioso servicio de catering, paellas y eventos gastronómicos en Pereira y el Eje Cafetero. 
Tu tono de voz es sumamente cálido, educado, servicial, apasionado por la buena comida y profesional. Tu objetivo principal es atender las dudas de los clientes, guiarlos en la elección de sus menús y recopilar los datos necesarios para generar una cotización.

INSTRUCCIONES DE INTERACCIÓN Y FLUIDEZ:
1. Saluda siempre con amabilidad y pregunta el nombre del cliente si no lo ha proporcionado.
2. Identifica la necesidad del cliente (¿Busca una paella a domicilio?, ¿Un asado al barril?, ¿Catering para un evento específico?, ¿Pasabocas/Mesas de quesos?).
3. Realiza preguntas de manera orgánica (una o dos a la vez) para recopilar los siguientes datos clave:
   - Nombre del cliente.
   - Fecha y hora aproximada del evento o entrega.
   - Número de personas / porciones necesarias (Recordar amablemente que en paellas el pedido mínimo es de 3 porciones).
   - Tipo de plato o menú de interés.
   - Preferencias o restricciones alimenticias (si hay vegetarianos, veganos o alergias).
   - Tipo de servicio deseado (Comida lista a domicilio vs. Preparación in situ con chef).
   - Preferencia de empaque para paellas (Paellera prestada o recipiente desechable).
4. Si el cliente solicita fotos, utiliza únicamente los recursos autorizados de la galería de imágenes del catálogo (Paellas, Asados, Pasabocas, Tablas de Quesos) sin saturar la conversación con demasiados archivos a la vez.

REGLAS DE PRECIOS Y COTIZACIÓN:
- Proporciona valores de referencia o rangos de precios basados en la Base de Conocimiento.
- Aclara que el valor final o personalizado será confirmado por el equipo comercial/Ana María al consolidar los detalles del domicilio o requerimientos especiales del evento.

REGLAS DE TRASPASO A HUMANO (HUMAN HANDOVER):
- Si el cliente proporciona toda la información requerida para su cotización, genera un resumen claro de la solicitud y dile:
  "¡Excelente! He registrado todos los detalles de tu evento/pedido. En breve Ana María o un asesor de nuestro equipo se pondrá en contacto contigo para confirmar disponibilidad y finalizar los detalles de tu reserva."
- Si el cliente escribe explícitamente frases como "quiero hablar con una persona", "pásame con un humano", "quiero hablar con Ana María" o si hay un problema complejo:
  Responde inmediatamente con cortesía: "Con mucho gusto. En este momento transfiero tu chat a nuestro equipo comercial para que te atienda personalmente." y activa la alerta de transferencia.

MANEJO DE SEGUIMIENTO E INACTIVIDAD:
- Si el cliente deja de responder durante 1 hora a mitad de una cotización:
  Envía un mensaje sutil: "Hola [Nombre], ¿sigues por aquí? Quedo atento si deseas que continuemos con la cotización de tu pedido con Ana María Gourmet."
- Si pasan 30 minutos adicionales sin respuesta:
  Cierra amablemente: "Parece que estás ocupado/a en este momento. Dejaré tu cotización pausada. Cuando desees retomar, solo escríbenos por aquí. ¡Que tengas un excelente día!"

RESTRICCIONES Y SEGURIDAD:
- Mantén siempre una postura educada. Si el usuario utiliza lenguaje ofensivo o inapropiado, responde con respeto e indica que das por finalizada la conversación.
- No respondas preguntas ajenas al menú, servicios o gastronomía de Ana María Gourmet."""

kb_text = """# BASE DE CONOCIMIENTO: ANA MARÍA GOURMET

## 1. INFORMACIÓN DE LA EMPRESA
- Nombre comercial: Ana María Gourmet
- Descripción: Servicio de catering premium, paellas tradicionales, asados al barril, banquetes, tablas de quesos, pasabocas gourmet y menús corporativos/familiares para eventos en Pereira y eje cafetero.
- Valores: Alta gastronomía, ingredientes frescos, presentación impecable, atención cálida y personalizada.
- Ubicación / Cobertura: Pereira, Dosquebradas y zonas aledañas (servicio a domicilio o preparación in situ/eventos).

## 2. PORTAFOLIO DE PRODUCTOS Y SERVICIOS

### A. PAELLAS TRADICIONALES Y ESPECIALES
- Variedades disponibles:
  - Paella Marinera (mariscos seleccionados)
  - Paella Valenciana (carnes de cerdo, pollo y vegetales)
  - Paella Mixta (mariscos y carnes)
  - Paella Vegana / Vegetariana (vegetales frescos de temporada)
- Condición de pedido mínimo: A partir de 3 porciones en adelante.
- Modalidad de entrega:
  - En Paellera tradicional (se presta para el evento y se recoge posteriormente).
  - En recipiente desechable de presentación elegante (ideal si el cliente no puede devolver la paellera).
- Incluye: Acompañamiento de pan gourmet porción por persona.

### B. ASADOS AL BARRIL Y CARNES
- Cortes de carne seleccionados (Res, Cerdo, Pollo, Chorizos artesanos).
- Modalidad: Servicio de preparación e instalación en el sitio del evento (in situ) o despacho listo para consumir.
- Presentación del personal: Chefs/asadores uniformados para eventos.

### C. MENÚS DE PLATO FUERTE PARA EVENTOS
El cliente puede armar su plato eligiendo:
- Proteína: Lomo de cerdo, Pechuga de pollo en salsas gourmet, Lomo de res estrogonoff, etc.
- Acompañamiento / Carbohidrato: Arroz al curry, Arroz verde, Papa gratinada/al horno.
- Ensalada: Ensalada gourmet, ensalada mediterránea, ensalada marinera, ensalada italiana.

### D. PASABOCAS, CANAPÉS Y MESAS TEMÁTICAS
- Tablas de quesos y madurados (para 10, 20, 30+ personas).
- Mesas de pasabocas para bodas, 15 años y eventos corporativos.
- Pasabocas por bandeja / unidad (Albondiguitas gourmet, brochetas, canapés variados).

### E. POSTRES
- Variedad de repostería fina para eventos bajo pedido.

## 3. POLÍTICAS COMERCIALES Y DE SERVICIO
- Anticipación de pedidos:
  - Paellas pequeñas/medianas: Mínimo 24 - 48 horas de anticipación.
  - Eventos grandes / Catering (>20 personas): Mínimo 3 a 5 días de anticipación.
- Domicilio: Incluido o con recargo dependiendo de la distancia y el sector de entrega.
- Formas de Pago: Transferencia bancaria (Bancolombia/Nequi/Daviplata) o efectivo contra entrega."""

custom_fields = [
    {
        "name": "nombre_cliente",
        "label": "Nombre del Cliente",
        "type": "text",
        "required": True,
        "description": "Nombre completo del cliente"
    },
    {
        "name": "fecha_hora_evento",
        "label": "Fecha y Hora del Evento / Entrega",
        "type": "text",
        "required": True,
        "description": "Fecha y hora estimada del evento o pedido"
    },
    {
        "name": "num_personas",
        "label": "Número de Personas / Porciones",
        "type": "text",
        "required": True,
        "description": "Cantidad de comensales o porciones (mínimo 3 en paellas)"
    },
    {
        "name": "tipo_servicio",
        "label": "Tipo de Servicio / Menú",
        "type": "text",
        "required": True,
        "description": "Paellas, Asado al barril, Menú plato fuerte, Pasabocas o Tablas de quesos"
    },
    {
        "name": "modalidad_servicio",
        "label": "Modalidad",
        "type": "text",
        "required": False,
        "description": "Comida lista a domicilio vs Preparación in situ con chef"
    },
    {
        "name": "preferencia_empaque",
        "label": "Empaque de Paella",
        "type": "text",
        "required": False,
        "description": "Paellera tradicional prestada vs Recipiente desechable"
    },
    {
        "name": "restricciones_alimenticias",
        "label": "Restricciones / Preferencias",
        "type": "text",
        "required": False,
        "description": "Vegetarianos, veganos, alergias u observaciones especiales"
    }
]

def main():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        agent_id = uuid.uuid4().hex
        user_id = "2d5fc55e-48e7-43bc-8d3e-624167bdae76"

        new_agent = Agent(
            id=agent_id,
            user_id=user_id,
            name="Anita Gourmet",
            description="Asistente virtual de atención al cliente de Ana María Gourmet (Catering, Paellas y Eventos en Pereira)",
            system_prompt=system_prompt,
            provider="vertex",
            model="gemini-2.5-flash",
            temperature=0.3,
            max_tokens=1024,
            status="active",
            channels=["web", "whatsapp"],
            notification_phone=None,
            custom_fields=custom_fields
        )

        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)

        print("SUCCESS: AGENTE CREADO EXITOSAMENTE:")
        print(f"   - ID: {new_agent.id}")
        print(f"   - Nombre: {new_agent.name}")
        print(f"   - Modelo: {new_agent.model} ({new_agent.provider})")
        print(f"   - Estado: {new_agent.status}")

        # Indexar Base de Conocimiento
        print("Indexing Base de Conocimiento RAG...")
        kb_bytes = kb_text.encode("utf-8")
        try:
            doc = process_and_index_document(
                db=db,
                agent_id=new_agent.id,
                filename="Base_de_Conocimiento_Ana_Maria_Gourmet.txt",
                content_type="text/plain",
                file_bytes=kb_bytes
            )
            print("SUCCESS: BASE DE CONOCIMIENTO INDEXADA:")
            print(f"   - Doc ID: {doc.id}")
            print(f"   - Chunks: {doc.chunk_count}")
        except Exception as ke:
            print(f"WARN: Nota al indexar embeddings en RAG: {ke}")

    except Exception as e:
        print("ERROR:", e)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
