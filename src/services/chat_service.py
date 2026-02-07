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

import asyncio
import logging
import time
from typing import Any, Dict, Generator, List, Optional

from langchain_ollama import ChatOllama

from core.config import get_settings
from services.cache_service import get_cache
from services.db_service import (
    clear_chat_history_from_db,
    get_chat_history_from_db,
    save_chat_message,
)
from services.memory_service import search_similar_chunks

logger = logging.getLogger(__name__)


class ChatService:
    """
    Service layer for chat functionality.
    Handles RAG, conversation history, and LLM interactions.
    """

    def __init__(self):
        self.settings = get_settings()

        if self.settings.llm.provider == "mistral":
            try:
                from langchain_mistralai import ChatMistralAI

                self.llm = ChatMistralAI(
                    model=self.settings.llm.model,
                    temperature=self.settings.llm.temperature,
                    mistral_api_key=self.settings.llm.api_key,
                )
            except ImportError:
                logger.warning(
                    "langchain-mistralai not installed. Falling back to Ollama."
                )
                self.llm = ChatOllama(
                    model=self.settings.llm.model,
                    temperature=self.settings.llm.temperature,
                    base_url=self.settings.llm.base_url,
                )
        else:
            self.llm = ChatOllama(
                model=self.settings.llm.model,
                temperature=self.settings.llm.temperature,
                base_url=self.settings.llm.base_url,
            )
        self.max_history = 10  # Keep last N conversation turns

    # ==================== Context Retrieval ====================

    def retrieve_context(
        self,
        query: str,
        collection_name: str = "global_memory",
        k: int = 4,
        session_id: Optional[str] = None,
        source_id: Optional[str] = None,
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
                source_id=source_id,
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

    def add_to_history(self, session_id: str, role: str, content: str) -> None:
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
        for msg in history[-self.max_history :]:
            role = "User" if msg["role"] == "user" else "Assistant"
            formatted.append(f"{role}: {msg['content']}")

        return "\n".join(formatted)

    # ==================== Prompt Building ====================

    def build_system_prompt(self) -> str:
        """Build the system prompt for the AI assistant."""
        return """You are a helpful assistant providing clear, well-structured information.

RESPONSE STRUCTURE:
For every question, organize your answer as follows:

- Introduction: Brief overview (1 sentence)
- Concept Explanations: Explain each concept...
- Comparison: Highlight differences...

FORMATTING GUIDELINES:
- Output PLAIN TEXT only
- DO NOT use markdown formatting (no #, **, -, etc.)
- Use numbering for lists (1. 2. 3.) when comparing or listing points
- Use blank lines to separate sections for readability
- Keep explanations concise (2-3 sentences per concept)
- Match the user's language (Arabic or English)

EXAMPLE OUTPUT:

Containerization vs Virtualization

Containerization:
Containerization packages an application with its dependencies into a lightweight, portable container that shares the host operating system kernel. This makes containers fast to start, efficient with resources, and consistent across different environments.

Virtualization:
Virtualization creates a complete virtual machine with its own operating system, hardware emulation, and dedicated resources. Each VM runs independently with full isolation but requires more system resources and takes longer to start.

Key Differences:

1. Resource Usage: Containers share the host OS kernel and are lightweight, while VMs run separate OS instances and are heavier
2. Startup Speed: Containers start in seconds, VMs take minutes to boot
3. Isolation Level: VMs provide stronger isolation with separate OS, containers share the host OS
4. Use Cases: Containers are ideal for microservices and cloud applications, VMs are better for running multiple different operating systems
divide the answer into paragraphs and each paragraph should be less than 5 sentences and between each paragraph there should be a blank line \n\n
Your output renders directly as text - keep it clean, organized, and easy to read."""

    def build_rag_prompt(self, message: str, context: str, history: str = "") -> str:
        """
        Build the complete RAG prompt with context and history.
        """
        prompt_parts = [self.build_system_prompt()]

        if history:
            prompt_parts.append(f"\nCONVERSATION HISTORY:\n{history}")

        if context:
            prompt_parts.append(f"\nDOCUMENT CONTEXT:\n{context}")
        else:
            prompt_parts.append(
                "\nNOTE: No relevant context was found in the knowledgebase."
            )

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
        use_history: bool = True,
    ) -> Dict[str, Any]:
        """
        Process a chat message and return a response.

        Optimized with:
        - Semantic caching (Redis)
        - Parallel context + history retrieval
        - TTFT measurement

        Args:
            message: User's message
            session_id: Session identifier for history tracking
            source_id: Optional specific file identifier
            k: Number of context chunks to retrieve
            use_history: Whether to include conversation history

        Returns:
            Dictionary with answer, sources, and session_id
        """
        request_start = time.perf_counter()
        session_id = session_id or "default"
        logger.info(
            f"Chat request: '{message[:50]}...' (session={session_id}, source={source_id})"
        )

        # 🚀 OPTIMIZATION 1: Check semantic cache first
        cache = get_cache()
        cached_response = cache.get_cached_response(message, source_id)
        if cached_response:
            latency = time.perf_counter() - request_start
            logger.info(f"⚡ Cache hit! Response time: {latency:.3f}s")
            cached_response["latency_ms"] = int(latency * 1000)
            return cached_response

        # 🚀 OPTIMIZATION 2: Parallel context + history retrieval
        async def async_retrieve_context():
            return self.retrieve_context(
                message, k=k, session_id=session_id, source_id=source_id
            )

        async def async_get_history():
            if use_history and session_id != "default":
                return self.format_history_for_prompt(session_id)
            return ""

        # Run both in parallel
        (context, sources), history = await asyncio.gather(
            async_retrieve_context(), async_get_history()
        )

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

            # Calculate latency
            latency = time.perf_counter() - request_start
            logger.info(f"📊 Response generated in {latency:.3f}s")

            result = {
                "answer": answer,
                "sources": sources,
                "session_id": session_id,
                "context_found": bool(context),
                "latency_ms": int(latency * 1000),
            }

            # 🚀 OPTIMIZATION 3: Cache the response for future queries
            cache.cache_response(message, result, source_id)

            return result

        except Exception as e:
            logger.error(f"LLM error: {e}")
            return {
                "answer": f"Error: Failed to generate response. ({str(e)})",
                "sources": [],
                "session_id": session_id,
                "context_found": bool(context),
                "error": True,
            }

    def chat_stream(
        self,
        message: str,
        session_id: Optional[str] = None,
        source_id: Optional[str] = None,
        k: int = 4,
        use_history: bool = True,
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
        logger.info(
            f"Stream chat request: '{message[:50]}...' (session={session_id}, source={source_id})"
        )

        # 1. Retrieve context
        context, sources = self.retrieve_context(
            message, k=k, session_id=session_id, source_id=source_id
        )

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
