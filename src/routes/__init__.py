"""Routes module initialization."""
from routes.health import base_router
from routes.extraction import extraction_router
from routes.chat import chat_router
from routes.delete import documents_router

__all__ = ["base_router", "extraction_router", "chat_router", "documents_router"]
