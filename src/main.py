"""
DocuMind - Document Extraction Pipeline �
=============================================

This is the main entry point for the DocuMind FastAPI application.
It initializes the application, sets up lifecycle management (startup/shutdown),
and registers the API routers.

Key Responsibilities:
---------------------
1. **App Initialization**: Creates the `FastAPI` app instance with metadata.
2. **Lifecycle Management**: Handles database connections and model loading on startup.
3. **Route Registration**: Imports and includes routers from `src/routes`.
4. **Server Entry**: Provides a standard execution block for running via `python main.py`.

Usage:
------
Run the server directly:
    $ python src/main.py

Or using uvicorn:
    $ uvicorn src.main:app --reload
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager

from core.config import get_settings
from routes import base_router, extraction_router, chat_router, documents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application Lifespan Context Manager.

    This function handles events that occur before the application starts receiving requests
    and after it finishes handling requests. It is the modern replacement for
    `on_event("startup")` and `on_event("shutdown")`.

    Startup Actions:
    - Load configuration settings.
    - Log connection details for MongoDB and LLM.
    - (Future) Initialize database connections pools.

    Shutdown Actions:
    - Clean up resources.
    - Close database connections.
    """
    # --- STARTUP ---
    settings = get_settings()
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    print(f"📦 MongoDB: {settings.mongo.url}")
    print(f"🤖 LLM Model: {settings.llm.model}")

    yield

    # --- SHUTDOWN ---
    print("👋 Shutting down...")


# --- Application Setup ---
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
     DocuMind API 🧠
    
    An intelligent document extraction service that uses hybrid OCR and VLM 
    techniques to process documents, extract structured data, and enable RAG workflows.
    """,
    lifespan=lifespan,
)

# --- Router Registration ---
# base_router: Health checks and basic info
app.include_router(base_router)

# extraction_router: Core document processing endpoints (/api/v1/extract)
app.include_router(extraction_router)

# chat_router: Knowledgebase Q&A endpoints (/api/v1/chat)
app.include_router(chat_router)

# documents_router: Document delete files endpoints (/api/v1/documents) for delete file acourding source id if need
app.include_router(documents_router)


if __name__ == "__main__":
    """
    Standard Entry Point.

    Allows running the application directly as a script.
    Defaults to host 0.0.0.0 (accessible externally) on port 8007.
    """
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8007)
