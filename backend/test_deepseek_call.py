"""
Script to test the raw response from OpenRouter deepseek/deepseek-chat.
"""

import asyncio
import httpx
from config import settings
from services.ai_service import build_lead_tools

async def test_call():
    # Active agent custom fields
    custom_fields = [
        {'key': 'phone', 'label': 'Telefono', 'type': 'string', 'required': True},
        {'key': 'empresa_persona', 'label': 'Empresa o persona', 'type': 'string', 'required': False},
        {'key': 'temporalidad', 'label': 'Temporalidad (Horas/Días/Meses)', 'type': 'string', 'required': True},
        {'key': 'tipo_espacio', 'label': 'Tipo de espacio', 'type': 'string', 'required': True},
        {'key': 'no_personas', 'label': 'Número de personas', 'type': 'number', 'required': True},
        {'key': 'sede', 'label': 'Sede (Pinares/Pereira Plaza)', 'type': 'string', 'required': True},
        {'key': 'fecha_hora_reserva', 'label': 'Fecha/Hora Reserva', 'type': 'string', 'required': True}
    ]
    
    tools = build_lead_tools(custom_fields)
    
    system_prompt = (
        "Eres un agente comercial experto en coworking.\n"
        "[FECHA Y HORA ACTUAL (GMT-5 Colombia)]\n"
        "La fecha de hoy es: 2026-05-27\n"
        "El día de la semana es: miércoles\n"
        "La hora actual es: 18:24:26\n"
        "Usa esta información siempre que el usuario te pregunte por la fecha o la hora...\n"
        "[INSTRUCCIONES DE CAPTURA DE LEADS]\n"
        "Debes llamar a la herramienta 'save_lead_info' de inmediato cada vez que el usuario te revele cualquier dato nuevo (como su nombre, su teléfono, su correo, o cualquier otro campo de interés como la empresa, tipo de espacio, temporalidad, etc.).\n"
        "NO esperes a tener todos los datos para llamar a la función. Ve guardando y actualizando los datos de forma incremental paso a paso a medida que fluye la conversación."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "¡Hola! Bienvenido a Social&Co Coworking. Mi nombre es Socio, estoy aquí para ayudarte a encontrar el espacio perfecto para tus necesidades. Para comenzar, ¿podrías decirme tu nombre completo?"},
        {"role": "user", "content": "Guille"}
    ]
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": "https://genia.plataforma",
        "X-Title": "Plataforma Genia",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.1,
        "max_tokens": 1024,
    }
    
    async with httpx.AsyncClient() as client:
        print("Sending request to OpenRouter...")
        response = await client.post(url, headers=headers, json=payload, timeout=60.0)
        print(f"Status Code: {response.status_code}")
        print("Raw JSON Response:")
        print(response.text)

if __name__ == "__main__":
    asyncio.run(test_call())
