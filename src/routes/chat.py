"""
Chat Routes API 💬
==================

FastAPI routes for the DocuMind Chatbot.

Endpoints:
- POST /api/v1/chat/           - Standard chat (RAG-powered)
- POST /api/v1/chat/stream     - Streaming chat response (SSE)
- GET  /api/v1/chat/history/{session_id}  - Get conversation history
- DELETE /api/v1/chat/history/{session_id} - Clear conversation history
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    ClearHistoryResponse,
)
from controllers.chat_controller import ChatController

chat_router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat"],
)

# Singleton controller
_controller = None


def get_controller() -> ChatController:
    """Get or create the ChatController singleton."""
    global _controller
    if _controller is None:
        _controller = ChatController()
    return _controller


@chat_router.post("/", response_model=ChatResponse)
async def chat_with_documents(request: ChatRequest):
    """
    Chat with the knowledgebase using natural language.

    This endpoint:
    1. Searches indexed documents for relevant context
    2. Includes conversation history (if session_id provided)
    3. Generates an AI response using RAG

    Args:
        request: ChatRequest with message, optional session_id, and k parameter

    Returns:
        ChatResponse with answer, sources, and metadata
    """
    controller = get_controller()

    try:
        result = await controller.chat(
            message=request.message,
            session_id=request.session_id,
            source_id=request.source_id,
            k=request.k,
            use_history=request.use_history,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@chat_router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream a chat response using Server-Sent Events (SSE).

    This endpoint streams the response token by token for a
    more interactive user experience.

    Returns:
        StreamingResponse with text/event-stream content type
    """
    controller = get_controller()

    def generate():
        for token in controller.chat_stream(
            message=request.message,
            session_id=request.session_id,
            source_id=request.source_id,
            k=request.k,
            use_history=request.use_history,
        ):
            # SSE format: data: <content>\n\n
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@chat_router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str):
    """
    Get the conversation history for a session.

    Args:
        session_id: The session identifier

    Returns:
        ChatHistoryResponse with conversation history
    """
    controller = get_controller()
    result = controller.get_history(session_id)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@chat_router.delete("/history/{session_id}", response_model=ClearHistoryResponse)
async def clear_chat_history(session_id: str):
    """
    Clear the conversation history for a session.

    Args:
        session_id: The session identifier

    Returns:
        ClearHistoryResponse with success status
    """
    controller = get_controller()
    result = controller.clear_history(session_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Failed to clear history")
        )

    return result


@chat_router.get("/documents")
async def list_indexed_documents():
    """
    List all documents indexed in ChromaDB.

    Useful for debugging which documents are available for chat.

    Returns:
        Summary of indexed documents, total chunks, and sessions
    """
    from src.services.memory_service import get_indexed_documents

    return get_indexed_documents()


@chat_router.get("/sessions")
async def list_chat_sessions():
    """
    List all chat sessions stored in MongoDB.

    Returns:
        List of sessions with message counts and timestamps
    """
    from src.services.db_service import get_all_chat_sessions

    return {"sessions": get_all_chat_sessions()}


@chat_router.get("/cache/stats")
async def get_cache_stats():
    """
    Get semantic cache statistics.

    Returns:
        Cache stats including hit counts, cached responses, and TTL settings
    """
    from services.cache_service import get_cache

    cache = get_cache()
    return cache.get_stats()


@chat_router.delete("/cache")
async def clear_cache():
    """
    Clear all semantic cache entries.

    Use this when documents are updated and cached responses may be stale.

    Returns:
        Number of cache entries deleted
    """
    from services.cache_service import get_cache

    cache = get_cache()
    deleted = cache.clear_all()
    return {"success": True, "deleted_entries": deleted}
