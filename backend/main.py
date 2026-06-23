"""
Aplicación FastAPI Principal de PLATAFORMA GENIA.

Levanta el servidor ASGI, inicializa la base de datos SQLite, registra
los middlewares de CORS y define las rutas principales y endpoints de utilidad.
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from services.auth_service import get_current_user


from config import settings
from database import init_db
from routers import (
    agents_router,
    chat_router,
    conversations_router,
    dashboard_router,
    knowledge_router,
    leads_router,
    whatsapp_router,
    mcp_router,
    public_api_router,
)


import os

# ── Configuración de Logging ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ── Eventos de Ciclo de Vida (Lifespan) ────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialización de servicios en el inicio y cierre de la app."""
    logger.info("Iniciando PLATAFORMA GENIA Backend...")
    try:
        init_db()
    except Exception as e:
        logger.error(
            "Error al inicializar la base de datos: %s", str(e), exc_info=True
        )
    yield
    logger.info("Apagando PLATAFORMA GENIA Backend...")


# ── Instancia de FastAPI ──────────────────────────────────────────────
app = FastAPI(
    title="PLATAFORMA GENIA API",
    description="Backend de Automatización de Agentes de IA y Captura de Leads",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Middleware de CORS (lista blanca por ALLOWED_ORIGINS) ──────────────
# Los origenes permitidos se leen EXCLUSIVAMENTE desde Settings/entorno
# (ALLOWED_ORIGINS). Se permite un origen si y solo si esta en la lista
# configurada (sin comodines / wildcard). Requisito 7.2.
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

allowed_origins = settings.allowed_origins_list
if not allowed_origins and ENVIRONMENT != "production":
    # Fallback SOLO para desarrollo local si no se configuro ALLOWED_ORIGINS.
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Servir archivos de la biblioteca de imágenes ─────────────────────
# Solo montamos si el directorio existe o se puede crear (en local dev). 
# En producción (Vercel) usamos Supabase Storage, por lo que no es necesario local storage.
if os.path.exists("data/uploads"):
    app.mount("/static/uploads", StaticFiles(directory="data/uploads"), name="uploads")
else:
    try:
        os.makedirs("data/uploads", exist_ok=True)
        app.mount("/static/uploads", StaticFiles(directory="data/uploads"), name="uploads")
    except Exception as e:
        logger.warning(
            "No se pudo montar /static/uploads debido a restricciones de solo lectura del filesystem: %s",
            str(e)
        )


# ── Registro de Routers ───────────────────────────────────────────────
app.include_router(agents_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(chat_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(conversations_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(leads_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(dashboard_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(knowledge_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(whatsapp_router, prefix="/api")
app.include_router(mcp_router, prefix="/api", dependencies=[Depends(get_current_user)])

# Router publico B2B multi-tenant (auth por API key en sus propias dependencias).
app.include_router(public_api_router)



# ── Endpoints Globales / de Utilidad ──────────────────────────────────
@app.get("/", tags=["Health Check"])
def read_root():
    """Endpoint de verificación de estado básico (Health Check)."""
    return {
        "status": "online",
        "service": "PLATAFORMA GENIA Backend",
        "version": "1.0.0",
    }


@app.get("/test-client", response_class=HTMLResponse, tags=["Utilities"])
def get_test_client():
    """Retorna la consola de pruebas HTML autocontenida."""
    try:
        with open("test_client.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except Exception as e:
        return HTMLResponse(content=f"<h3>Error al cargar test_client.html: {str(e)}</h3>", status_code=500)



@app.get("/api/models", tags=["Utilities"])
def get_available_models():
    """
    Retorna la lista de modelos disponibles en cada proveedor.

    Utilizado por el frontend para poblar dinámicamente los selects de
    selección de modelos (tanto de Groq para chat, como de Gemini para RAG/etc).
    """
    return {
        "groq": settings.available_groq_models,
        "gemini": settings.available_gemini_models,
        "openrouter": settings.available_openrouter_models,
    }




# ── Manejadores de excepcion centralizados (11.2) ─────────────────────
# Mapean las excepciones de dominio a codigos HTTP sin exponer secretos ni
# detalles internos. Las credenciales/claves se leen siempre desde Settings/env.
from fastapi import Request  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from services.exceptions import DomainError  # noqa: E402
from services.providers.base import ModelUnavailableError  # noqa: E402


@app.exception_handler(DomainError)
async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    """
    Mapea las excepciones de dominio a su codigo HTTP:

    - AuthError -> 401, CrossTenantError -> 403, SubscriptionInactiveError -> 402,
      UsageLimitError -> 429.

    Devuelve solo un mensaje publico seguro (sin secretos ni stack traces).
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.public_message},
    )


@app.exception_handler(ModelUnavailableError)
async def handle_model_unavailable(
    request: Request, exc: ModelUnavailableError
) -> JSONResponse:
    """Mapea la indisponibilidad de todos los proveedores de modelo a HTTP 503."""
    logger.error("Todos los proveedores de modelo fallaron: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Servicio de modelo no disponible. Intente mas tarde."},
    )
