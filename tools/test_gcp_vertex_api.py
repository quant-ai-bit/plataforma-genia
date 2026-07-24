import os
import sys
import time
import json
from dotenv import load_dotenv

# Ensure UTF-8 output encoding for Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Load production env variables
load_dotenv('.env.prod.pulled')

print("=" * 60)
print("COMPROBACION DE APIS Y CREDENCIALES DE GOOGLE CLOUD / VERTEX AI")
print("=" * 60)

gemini_key = os.getenv("GEMINI_API_KEY", "")
gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
gcp_location = os.getenv("GOOGLE_CLOUD_LOCATION", "")
vertex_model = os.getenv("VERTEX_GEMINI_MODEL", "gemini-2.0-flash")
gcp_sa_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON", "")

print(f"Proyecto GCP: {gcp_project or 'No configurado'}")
print(f"Region GCP: {gcp_location or 'No configurado'}")
print(f"Modelo Vertex AI: {vertex_model}")
print(f"Gemini API Key presente: {'Si' if gemini_key else 'No'}")
print(f"Service Account JSON presente: {'Si' if gcp_sa_json else 'No'}")
print("-" * 60)

# Test 1: Direct Google Generative AI (Gemini 2.0 Flash)
if gemini_key:
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        print("Probando API de Google Gemini (gemini-2.0-flash)...")
        start_t = time.time()
        model = genai.GenerativeModel("gemini-2.0-flash")
        resp = model.generate_content("Hola, confirma que estas respondiendo desde Google Cloud Gemini 2.0 Flash.")
        duration = time.time() - start_t
        print(f"[OK] Respuesta exitosa en {duration:.2f}s:")
        print(f"     \"{resp.text.strip()}\"")
    except Exception as e:
        print(f"[ERROR] Error probando Gemini API Directa: {e}")
else:
    print("[WARN] GEMINI_API_KEY no encontrada en variables.")

print("-" * 60)

# Test 2: Vertex AI con Service Account Credentials (si aplica)
if gcp_sa_json or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    try:
        from google.oauth2 import service_account
        
        print("Verificando autenticacion con Service Account de GCP...")
        if gcp_sa_json:
            sa_info = json.loads(gcp_sa_json)
            credentials = service_account.Credentials.from_service_account_info(
                sa_info,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            print(f"[OK] Credenciales parsed correctamente.")
            print(f"     Client Email: {sa_info.get('client_email')}")
            print(f"     Project ID del JSON: {sa_info.get('project_id')}")
            print(f"     Private Key ID: {sa_info.get('private_key_id')}")
        else:
            print("[INFO] Usando GOOGLE_APPLICATION_CREDENTIALS por defecto.")
            
    except Exception as e:
        print(f"[ERROR] Al validar Service Account JSON: {e}")
else:
    print("[INFO] GCP_SERVICE_ACCOUNT_JSON no esta configurada localmente.")

print("=" * 60)
