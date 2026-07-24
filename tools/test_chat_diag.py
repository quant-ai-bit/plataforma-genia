import asyncio
import os
import sys
from dotenv import load_dotenv

# Add backend directory to sys.path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Force UTF-8 output encoding for Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv('.env.prod.pulled')

# Import settings and services
from config import settings
from services.providers.gemini_provider import GeminiProvider
from services.providers.base import GenerationRequest

async def test_gemini():
    print("GEMINI_API_KEY present in settings:", bool(settings.gemini_api_key))
    if not settings.gemini_api_key:
        print("GEMINI_API_KEY is missing/empty!")
        return
    gp = GeminiProvider(model="gemini-2.0-flash")
    req = GenerationRequest(
        messages=[{"role": "user", "content": "Hola, responde brevemente en español."}],
        system_prompt="Eres un asistente amable.",
        max_tokens=100,
        temperature=0.7
    )
    try:
        res = await gp.generate(req, timeout_s=15.0)
        print("SUCCESS! Gemini Answer:", res.text)
    except Exception as e:
        print("ERROR in GeminiProvider:", type(e).__name__, str(e))

if __name__ == "__main__":
    asyncio.run(test_gemini())
