import asyncio
import logging
import sys
import os

# Añadir el directorio base al path para poder importar
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from services.providers.gemini_provider import GeminiProvider
from services.providers.groq_provider import GroqProvider
from services.providers.openrouter_provider import OpenRouterProvider
from services.providers.base import GenerationRequest

logging.basicConfig(level=logging.WARNING)

async def test_model(provider_name, model_name):
    print(f"Testing {provider_name} : {model_name} ...", end=" ", flush=True)
    req = GenerationRequest(
        messages=[{"role": "user", "content": "Hi"}],
        system_prompt="You are a helper.",
        max_tokens=10,
        temperature=0.7
    )
    try:
        if provider_name == "gemini":
            provider = GeminiProvider(model=model_name)
        elif provider_name == "groq":
            provider = GroqProvider(model=model_name)
        elif provider_name == "openrouter":
            provider = OpenRouterProvider(model=model_name)
        else:
            print("UNKNOWN PROVIDER")
            return False, "Unknown provider"
            
        res = await provider.generate(req, timeout_s=10.0)
        text_preview = res.text.strip().replace('\n', ' ')[:40]
        print(f"SUCCESS! Output: '{text_preview}'")
        return True, None
    except Exception as e:
        err_str = str(e)
        print(f"FAILED! Error: {err_str[:120]}")
        return False, err_str

async def main():
    print("=== STARTING MODEL CONNECTIVITY TESTS ===")
    
    groq_models = settings.available_groq_models
    gemini_models = settings.available_gemini_models
    openrouter_models = settings.available_openrouter_models
    
    results = {}
    
    print("\n--- Testing Groq Models ---")
    for m in groq_models:
        ok, err = await test_model("groq", m)
        results[f"groq:{m}"] = {"ok": ok, "error": err}
        
    print("\n--- Testing Gemini Models ---")
    for m in gemini_models:
        ok, err = await test_model("gemini", m)
        results[f"gemini:{m}"] = {"ok": ok, "error": err}
        
    print("\n--- Testing OpenRouter Models ---")
    for m in openrouter_models:
        ok, err = await test_model("openrouter", m)
        results[f"openrouter:{m}"] = {"ok": ok, "error": err}
        
    print("\n=== SUMMARY OF RESULTS ===")
    working = []
    failed = []
    for k, v in results.items():
        if v["ok"]:
            working.append(k)
        else:
            failed.append((k, v["error"]))
            
    print(f"\n[WORKING MODELS ({len(working)}/{(len(working)+len(failed))}):]")
    for w in working:
        print(f" - {w}")
        
    print(f"\n[FAILED MODELS ({len(failed)}/{(len(working)+len(failed))}):]")
    for f_name, f_err in failed:
        print(f" - {f_name} => {f_err[:150]}")

if __name__ == "__main__":
    asyncio.run(main())
