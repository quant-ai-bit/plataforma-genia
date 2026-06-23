"""Entry point para Vercel Serverless Functions."""
import sys
import os

# Agregar el directorio backend al path para que los imports funcionen correctamente en Vercel
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Importar la app FastAPI desde el main de backend
from main import app
