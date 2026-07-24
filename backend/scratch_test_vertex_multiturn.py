import asyncio
import os
import json
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv

load_dotenv('.env.vercel.prod')

from services.providers.vertex_provider import VertexAIProvider
from services.providers.base import GenerationRequest

async def test():
    provider = VertexAIProvider(model="gemini-2.5-flash")
    
    # Test turn 1
    req1 = GenerationRequest(
        messages=[{"role": "user", "content": "Hola"}],
        system_prompt="Eres Sara, un asistente virtual.",
        max_tokens=500,
        temperature=0.7
    )
    res1 = await provider.generate(req1, 30.0)
    print("TURN 1 RES:", res1.text)

    # Test turn 2 with previous history including error message or normal history
    req2 = GenerationRequest(
        messages=[
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "⚠️ Hubo un error procesando tu solicitud con el servicio de IA. Por favor, inténtalo de nuevo más tarde."},
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "¡Hola! Es un gusto saludarte. Para empezar, ¿podrías indicarme tu nombre completo, por favor?"},
            {"role": "user", "content": "Felipe"}
        ],
        system_prompt="Eres Sara, un asistente virtual.",
        max_tokens=500,
        temperature=0.7
    )
    res2 = await provider.generate(req2, 30.0)
    print("TURN 2 RES:", res2.text)

if __name__ == "__main__":
    asyncio.run(test())
