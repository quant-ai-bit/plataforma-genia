"""
Configuración central de PLATAFORMA GENIA.

Usa pydantic-settings para cargar variables de entorno desde .env
y expone las listas de modelos disponibles por proveedor.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración global de la aplicación."""

    # Base de datos
    database_url: str = ""

    @property
    def effective_database_url(self) -> str:
        """Retorna la URL de base de datos efectiva. Cae en SQLite local si está vacía."""
        return self.database_url or "sqlite:///./data/genia.db"

    # Groq (LLM principal para chat)
    groq_api_key: str = ""

    # Google Gemini (embeddings, audio, visión)
    gemini_api_key: str = ""

    # OpenRouter
    openrouter_api_key: str = ""

    # Meta WhatsApp Cloud API
    meta_access_token: str = ""
    phone_number_id: str = ""
    webhook_verify_token: str = "genia_verify_token"
    meta_app_secret: str = ""

    # Supabase (JWT Secret para autenticación y almacenamiento)
    supabase_jwt_secret: str = ""
    supabase_url: str = ""
    supabase_service_key: str = ""

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"

    # --- Vertex AI / GCP (genia-agent-platform) ---
    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"
    # Ruta a un archivo JSON de service account (ideal en local).
    google_application_credentials: str = ""
    # Contenido JSON del service account (ideal para Vercel / serverless).
    # Se lee solo desde el entorno (GCP_SERVICE_ACCOUNT_JSON); nunca en codigo.
    gcp_service_account_json: str = ""
    vertex_gemini_model: str = "gemini-1.5-pro"

    # --- Orquestacion de modelos (timeout / retry / fallback) ---
    model_timeout_s: float = 30.0
    model_max_retries: int = 1
    model_fallback_order: str = "vertex,groq,openrouter"

    @property
    def available_groq_models(self) -> list[str]:
        """Modelos disponibles en Groq."""
        return [
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "llama3-70b-8192",
            "llama3-8b-8192",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ]

    @property
    def available_gemini_models(self) -> list[str]:
        """Modelos disponibles en Google Gemini."""
        return [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]

    @property
    def available_openrouter_models(self) -> list[str]:
        """Modelos disponibles en OpenRouter."""
        return [
            "deepseek/deepseek-chat",
            "anthropic/claude-3.5-sonnet:beta",
            "google/gemini-2.5-flash",
            "openai/gpt-4o-mini",
            "openai/gpt-4o",
        ]

    # --- Seguridad / API publica multi-tenant ---
    # Pepper secreto para el hashing de API keys (SHA-256 + pepper).
    # Se carga desde la variable de entorno API_KEY_PEPPER (nunca hardcodear).
    api_key_pepper: str = ""

    # Lista blanca de origenes permitidos para CORS (separados por comas).
    # Se carga desde ALLOWED_ORIGINS; vacio = sin origenes adicionales.
    allowed_origins: str = ""

    # --- Cobros Bre-B (genia-agent-platform) ---
    # Reemplaza el billing de Stripe por cobros Bre-B verificados por vision.
    # Todas las claves se leen exclusivamente desde el entorno; nunca en codigo.
    # breb_llave: llave Bre-B del comercio destino de los cobros.
    # breb_titular: nombre del titular asociado a la llave (informativo).
    # subscription_amount_cop: monto mensual del cobro en centavos de COP.
    breb_llave: str = ""
    breb_titular: str = ""
    subscription_amount_cop: int = 5000000

    # --- MCP saliente del tenant con-tranqui ---
    # URL base y token de servicio del servidor MCP remoto de con-tranqui.
    # Se leen solo desde el entorno (CONTRANQUI_MCP_URL / CONTRANQUI_MCP_SERVICE_TOKEN).
    contranqui_mcp_url: str = ""
    contranqui_mcp_service_token: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        """Devuelve la lista blanca de origenes CORS a partir de `allowed_origins`."""
        return [o.strip() for o in (self.allowed_origins or "").split(",") if o.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()