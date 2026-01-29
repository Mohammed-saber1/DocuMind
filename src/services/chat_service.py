"""
Chat Service 💬
===============

This service handles all chat-related business logic including:
- Conversation history management
- Context retrieval from ChromaDB
- LLM interaction and response generation
- Streaming support

Architecture follows the Controller -> Service -> Repository pattern.
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional, Generator
from datetime import datetime

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from services.memory_service import search_similar_chunks
from services.db_service import (
    save_chat_message,
    get_chat_history_from_db,
    clear_chat_history_from_db
)
from core.config import get_settings
from utils.file_utils import calculate_file_hash

logger = logging.getLogger(__name__)

class ChatService:
    """
    Service layer for chat functionality.
    Handles RAG, conversation history, and LLM interactions.
    """

    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatOllama(
            model=self.settings.llm.model,
            temperature=self.settings.llm.temperature,
            base_url=self.settings.llm.base_url
        )
        self.max_history = 10  # Keep last N conversation turns

    # ==================== Context Retrieval ====================

    def retrieve_context(
        self, 
        query: str, 
        collection_name: str = "global_memory",
        k: int = 4,
        session_id: Optional[str] = None,
        source_id: Optional[str] = None
    ) -> tuple[str, List[str]]:
        """
        Retrieve relevant context from ChromaDB for RAG.
        
        Args:
            query: User's question
            collection_name: ChromaDB collection to search
            k: Number of results to retrieve
            session_id: Optional filter by session
            source_id: Optional filter by specific file
            
        Returns:
            tuple: (context_text, list of source references)
        """
        try:
            results = search_similar_chunks(
                query, 
                collection_name=collection_name, 
                k=k, 
                session_id=session_id,
                source_id=source_id
            )
            
            context_parts = []
            sources = []
            
            for doc in results:
                context_parts.append(doc.page_content)
                source = doc.metadata.get("source", "unknown")
                doc_id = doc.metadata.get("doc_id", "unknown")
                sources.append(f"{source} (ID: {doc_id})")
            
            # Deduplicate sources
            sources = list(set(sources))
            context_text = "\n---\n".join(context_parts)
            
            return context_text, sources
            
        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            return "", []

    # ==================== Conversation History (MongoDB) ====================

    def add_to_history(
        self, 
        session_id: str, 
        role: str, 
        content: str
    ) -> None:
        """Add a message to the conversation history in MongoDB."""
        save_chat_message(session_id, role, content)

    def get_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for a session from MongoDB."""
        return get_chat_history_from_db(session_id, limit=self.max_history * 2)

    def clear_history(self, session_id: str) -> None:
        """Clear conversation history for a session from MongoDB."""
        clear_chat_history_from_db(session_id)

    def format_history_for_prompt(self, session_id: str) -> str:
        """Format conversation history into a string for the prompt."""
        history = self.get_history(session_id)
        if not history:
            return ""
        
        formatted = []
        for msg in history[-self.max_history:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            formatted.append(f"{role}: {msg['content']}")
        
        return "\n".join(formatted)

    # ==================== Prompt Building ====================

    def build_system_prompt(self) -> str:
        """Build the system prompt for the AI assistant."""
        return """You are the Orbit AI Assistant, a helpful expert that answers questions based on the provided document context.

INSTRUCTIONS:
- Use ONLY the context provided to answer the user's question accurately.
- For structured data (Excel/CSV), look for EXACT matches in the context.
- If the answer is not in the context, say: "I'm sorry, I don't have enough information in my knowledgebase to answer that."
- NEVER make up or infer data that isn't explicitly stated in the context.
- Be concise, clear, and professional.
- Match the language of the context (Arabic or English).
- When answering from Excel/CSV data, cite the specific row or sheet if available."""

    def build_rag_prompt(
        self,
        message: str,
        context: str,
        history: str = ""
    ) -> str:
        """
        Build the complete RAG prompt with context and history.
        """
        prompt_parts = [self.build_system_prompt()]
        
        if history:
            prompt_parts.append(f"\nCONVERSATION HISTORY:\n{history}")
        
        if context:
            prompt_parts.append(f"\nDOCUMENT CONTEXT:\n{context}")
        else:
            prompt_parts.append("\nNOTE: No relevant context was found in the knowledgebase.")
        
        prompt_parts.append(f"\nUSER QUESTION:\n{message}")
        prompt_parts.append("\nASSISTANT RESPONSE:")
        
        return "\n".join(prompt_parts)

    # ==================== Chat Methods ====================

    async def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        source_id: Optional[str] = None,
        k: int = 4,
        use_history: bool = True
    ) -> Dict[str, Any]:
        """
        Process a chat message and return a response.
        
        Args:
            message: User's message
            session_id: Session identifier for history tracking
            source_id: Optional specific file identifier
            k: Number of context chunks to retrieve
            use_history: Whether to include conversation history
            
        Returns:
            Dictionary with answer, sources, and session_id
        """
        session_id = session_id or "default"
        logger.info(f"Chat request: '{message[:50]}...' (session={session_id}, source={source_id})")
        
        # 1. Retrieve context from ChromaDB
        context, sources = self.retrieve_context(message, k=k, session_id=session_id, source_id=source_id)
        
        # 2. Get conversation history
        history = ""
        if use_history and session_id != "default":
            history = self.format_history_for_prompt(session_id)
        
        # 3. Build prompt
        prompt = self.build_rag_prompt(message, context, history)
        
        # 4. Call LLM (async for better performance)
        try:
            response = await self.llm.ainvoke(prompt)
            answer = response.content if hasattr(response, "content") else str(response)
            answer = answer.strip()
            
            # 5. Save to history
            if session_id != "default":
                self.add_to_history(session_id, "user", message)
                self.add_to_history(session_id, "assistant", answer)
            
            return {
                "answer": answer,
                "sources": sources,
                "session_id": session_id,
                "context_found": bool(context)
            }
            
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return {
                "answer": f"Error: Failed to generate response. ({str(e)})",
                "sources": [],
                "session_id": session_id,
                "context_found": bool(context),
                "error": True
            }

    def chat_stream(
        self,
        message: str,
        session_id: Optional[str] = None,
        source_id: Optional[str] = None,
        k: int = 4,
        use_history: bool = True
    ) -> Generator[str, None, None]:
        """
        Stream a chat response token by token.
        
        Args:
            message: User's message
            session_id: Session identifier
            source_id: Optional specific file identifier
            k: Number of context chunks
            use_history: Include history
            
        Yields:
            String chunks of the response
        """
        session_id = session_id or "default"
        logger.info(f"Stream chat request: '{message[:50]}...' (session={session_id}, source={source_id})")
        
        # 1. Retrieve context
        context, sources = self.retrieve_context(message, k=k, session_id=session_id, source_id=source_id)
        
        # 2. Get conversation history
        history = ""
        if use_history and session_id != "default":
            history = self.format_history_for_prompt(session_id)
        
        # 3. Build prompt
        prompt = self.build_rag_prompt(message, context, history)
        
        # 4. Stream from LLM
        try:
            full_response = []
            for chunk in self.llm.stream(prompt):
                token = chunk.content if hasattr(chunk, "content") else str(chunk)
                full_response.append(token)
                yield token
            
            # 5. Save complete response to history
            if session_id != "default":
                complete_answer = "".join(full_response)
                self.add_to_history(session_id, "user", message)
                self.add_to_history(session_id, "assistant", complete_answer)
                
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"\n\nError: {str(e)}"


# Singleton instance
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Get or create the ChatService singleton."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
