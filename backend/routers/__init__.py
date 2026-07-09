"""Paquete de routers de API para PLATAFORMA GENIA."""

from routers.agents import router as agents_router
from routers.chat import router as chat_router
from routers.conversations import router as conversations_router
from routers.dashboard import router as dashboard_router
from routers.knowledge import router as knowledge_router
from routers.leads import router as leads_router
from routers.whatsapp import router as whatsapp_router
from routers.mcp import router as mcp_router
from routers.public_api import router as public_api_router
from routers.google_calendar import router as google_calendar_router
from routers.free_models import router as free_models_router

__all__ = [
    "agents_router",
    "chat_router",
    "conversations_router",
    "leads_router",
    "dashboard_router",
    "knowledge_router",
    "whatsapp_router",
    "mcp_router",
    "public_api_router",
    "google_calendar_router",
    "free_models_router",
]


