"""
Chat Controller 🎮
==================

Controller for the Saber Orbit Chatbot.
Handles API request validation and delegates to ChatService for business logic.

This follows the Controller -> Service pattern for clean separation of concerns.
"""
import logging
from typing import Optional

from controllers.base_controller import BaseController
from services.chat_service import get_chat_service, ChatService

logger = logging.getLogger(__name__)


class ChatController(BaseController):
    """
    Controller for chat API endpoints.
    Thin layer that validates input and delegates to ChatService.
    """

    def __init__(self):
        super().__init__()
        self.chat_service: ChatService = get_chat_service()

    async def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        source_id: Optional[str] = None,
        k: int = 4,
        use_history: bool = True
    ) -> dict:
        """
        Process a chat message and return a response.
        
        Args:
            message: User's message/question
            session_id: Optional session ID for conversation tracking
            source_id: Optional specific file identifier
            k: Number of context chunks to retrieve (1-10)
            use_history: Whether to include conversation history
            
        Returns:
            Dictionary with answer, sources, and metadata
        """
        # Validate input
        if not message or not message.strip():
            return {
                "answer": "Please provide a message.",
                "sources": [],
                "session_id": session_id,
                "error": True
            }
        
        # Clamp k to reasonable range
        k = max(1, min(10, k))
        
        # Delegate to service
        return await self.chat_service.chat(
            message=message.strip(),
            session_id=session_id,
            source_id=source_id,
            k=k,
            use_history=use_history
        )

    def chat_stream(
        self,
        message: str,
        session_id: Optional[str] = None,
        source_id: Optional[str] = None,
        k: int = 4,
        use_history: bool = True
    ):
        """
        Stream a chat response.
        
        Yields tokens from the LLM response.
        """
        if not message or not message.strip():
            yield "Please provide a message."
            return
        
        k = max(1, min(10, k))
        
        yield from self.chat_service.chat_stream(
            message=message.strip(),
            session_id=session_id,
            source_id=source_id,
            k=k,
            use_history=use_history
        )

    def get_history(self, session_id: str) -> dict:
        """
        Get conversation history for a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Dictionary with history and metadata
        """
        if not session_id:
            return {"history": [], "error": "session_id is required"}
        
        history = self.chat_service.get_history(session_id)
        return {
            "session_id": session_id,
            "history": history,
            "message_count": len(history)
        }

    def clear_history(self, session_id: str) -> dict:
        """
        Clear conversation history for a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Success status
        """
        if not session_id:
            return {"success": False, "error": "session_id is required"}
        
        self.chat_service.clear_history(session_id)
        return {
            "success": True,
            "session_id": session_id,
            "message": "History cleared"
        }
