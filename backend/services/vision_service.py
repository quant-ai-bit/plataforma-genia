"""
Servicio de Visión y Entrenamiento de Prompts para PLATAFORMA GENIA.

Utiliza el modelo gemini-2.5-flash para analizar las imágenes de los agentes o
generar reglas de entrenamiento basadas en la información ingresada por el usuario.
"""

import json
import logging
import google.generativeai as genai
from config import settings

logger = logging.getLogger(__name__)

# Configurar el SDK de Google Generative AI
if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)
else:
    logger.warning("GEMINI_API_KEY no está configurada. El análisis y entrenamiento visual no funcionarán.")


def analyze_image_for_agent(image_bytes: bytes, mime_type: str) -> dict:
    """
    Analiza una imagen cargada usando Gemini Vision y devuelve información estructurada
    para entrenar al agente.

    Args:
        image_bytes: Contenido binario de la imagen.
        mime_type: Tipo MIME de la imagen.

    Returns:
        Un diccionario con: detected_product, description, keywords, suggested_rule.
    """
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY no está configurada en las variables de entorno.")

    try:
        logger.info("Enviando imagen (%s) a gemini-2.5-flash para análisis visual...", mime_type)
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = (
            "Analiza detalladamente esta imagen de un producto, espacio físico, coworking, oficina, servicio o recurso, "
            "e identifica a qué corresponde. Escribe todos los campos de respuesta en español.\n\n"
            "Devuelve un objeto JSON con los siguientes campos obligatorios:\n"
            "- 'detected_product': El nombre exacto o título del producto, espacio o recurso (máx 5 palabras).\n"
            "- 'description': Una descripción detallada y profesional de la imagen para que el agente de IA la entienda.\n"
            "- 'keywords': Palabras clave o frases de búsqueda separadas por comas que el cliente usaría para preguntar por este elemento (ej. 'sala de juntas, sala Pereira, fotos de sala').\n"
            "- 'suggested_rule': Una instrucción clara e imperativa para el Prompt del Sistema del agente que le indique bajo qué intención/palabras del usuario debe incluir/mostrar exactamente esta imagen utilizando la sintaxis de Markdown e insertando el placeholder {url} exacto de la imagen (ej. 'Si el cliente pregunta por la sala de juntas, salas de reuniones o fotos de los espacios, debes responder de forma entusiasta mostrando la imagen usando: ![Sala de Juntas]({url})').\n"
        )

        response = model.generate_content(
            [prompt, {"mime_type": mime_type, "data": image_bytes}],
            generation_config={"response_mime_type": "application/json"}
        )

        # Parsear la respuesta estructurada
        data = json.loads(response.text)
        logger.info("Análisis de visión completado con éxito. Producto: %s", data.get("detected_product"))
        return data

    except Exception as e:
        logger.error("Error al analizar la imagen con Gemini Vision: %s", str(e), exc_info=True)
        # Fallback seguro
        return {
            "detected_product": "Imagen de Producto",
            "description": "Imagen cargada a la biblioteca del agente.",
            "keywords": "foto, imagen",
            "suggested_rule": "Si el cliente solicita ver una foto o imagen de este producto, muéstrala usando: ![Imagen]({url})"
        }


def generate_image_training_rule(product_name: str, description: str, price: str, url: str) -> dict:
    """
    Genera reglas de prompt basadas en la información textual del producto/servicio/espacio
    proporcionada por el usuario, utilizando el modelo de lenguaje de Gemini.

    Args:
        product_name: Nombre del producto o servicio.
        description: Descripción del producto o servicio.
        price: Precio del producto o servicio.
        url: URL pública donde está guardada la imagen.

    Returns:
        Un diccionario con: keywords, suggested_rule.
    """
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY no está configurada en las variables de entorno.")

    try:
        logger.info("Generando regla de entrenamiento de prompt para el producto '%s'...", product_name)
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = (
            "Eres un experto en ingeniería de prompts para agentes conversacionales de IA.\n"
            "Un usuario ha cargado una imagen y ha proporcionado los siguientes datos de un producto, espacio o servicio:\n"
            f"- Nombre: {product_name}\n"
            f"- Descripción: {description}\n"
            f"- Precio: {price}\n"
            f"- URL de la imagen: {url}\n\n"
            "Tu tarea es generar sugerencias en español para entrenar al agente conversacional sobre cómo y cuándo usar esta imagen.\n"
            "Devuelve un objeto JSON con los siguientes campos obligatorios:\n"
            "- 'keywords': Una lista de palabras clave o frases de búsqueda separadas por comas (ej. 'sala de juntas, sala Pereira, fotos de sala') que el cliente usaría en el chat para preguntar por este elemento.\n"
            "- 'suggested_rule': Una instrucción clara e imperativa para el Prompt del Sistema del agente que le indique bajo qué intención/palabras del usuario debe responder mostrando esta imagen exacta usando la sintaxis de Markdown e insertando la URL exacta provista: ![Nombre]({url}). Asegúrate de incluir el precio y los detalles clave en la instrucción para que el agente proporcione información correcta.\n"
        )

        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )

        data = json.loads(response.text)
        logger.info("Reglas de entrenamiento generadas con éxito para '%s'.", product_name)
        return data

    except Exception as e:
        logger.error("Error al generar reglas de prompt con Gemini: %s", str(e), exc_info=True)
        # Fallback seguro
        return {
            "keywords": f"{product_name.lower()}",
            "suggested_rule": f"Si el cliente pregunta por '{product_name}', describe el producto y muestra la foto usando: ![{product_name}]({url})"
        }


def extract_payment_receipt(image_bytes: bytes, mime_type: str) -> dict:
    """
    Extrae los datos de un comprobante de pago Bre-B usando Gemini Vision.

    Analiza la imagen de un comprobante/recibo de transferencia y devuelve sus
    campos estructurados para que el Agente de Verificacion de Pagos pueda
    compararlos contra el cobro esperado (monto, llave destino, referencia, etc.).

    Args:
        image_bytes: Contenido binario de la imagen del comprobante.
        mime_type: Tipo MIME de la imagen (p. ej. image/png, image/jpeg).

    Returns:
        Un diccionario con las claves:
        - 'monto': importe pagado tal como aparece (texto/numero).
        - 'llave_o_cuenta_destino': llave Bre-B, cuenta o destinatario.
        - 'referencia': numero de referencia/comprobante de la transaccion.
        - 'fecha': fecha de la transaccion tal como aparece.
        - 'estado': estado de la transaccion (aprobado/exitoso/rechazado/...).
        Devuelve un diccionario vacio si la imagen es ilegible o no contiene datos.
    """
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY no está configurada en las variables de entorno.")

    try:
        logger.info("Enviando comprobante (%s) a gemini-2.5-flash para extracción...", mime_type)
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = (
            "Eres un verificador de comprobantes de pago bancarios/Bre-B en Colombia. "
            "Analiza esta imagen de un comprobante de transferencia y extrae sus datos. "
            "Responde EXCLUSIVAMENTE con un objeto JSON con estos campos (en español):\n"
            "- 'monto': el importe transferido tal como aparece (ej. '50.000' o '50000').\n"
            "- 'llave_o_cuenta_destino': la llave Bre-B, numero de cuenta, celular o "
            "nombre del destinatario/beneficiario que recibe el dinero.\n"
            "- 'referencia': el numero de referencia, comprobante o transaccion.\n"
            "- 'fecha': la fecha (y hora si existe) de la transaccion tal como aparece.\n"
            "- 'estado': el estado de la operacion (ej. 'aprobado', 'exitoso', 'completado', "
            "'rechazado', 'pendiente').\n"
            "Si la imagen es ilegible o no es un comprobante de pago, devuelve un JSON vacío {}."
        )

        response = model.generate_content(
            [prompt, {"mime_type": mime_type, "data": image_bytes}],
            generation_config={"response_mime_type": "application/json"},
        )

        data = json.loads(response.text)
        if not isinstance(data, dict):
            return {}
        logger.info(
            "Extracción de comprobante completada (estado=%s, ref=%s)",
            data.get("estado"),
            data.get("referencia"),
        )
        return data

    except Exception as e:
        logger.error("Error al extraer datos del comprobante con Gemini Vision: %s", str(e), exc_info=True)
        # Devuelve vacio para que el servicio de cobros responda 422 (ilegible).
        return {}
