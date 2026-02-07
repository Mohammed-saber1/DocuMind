"""
Chat Schemas 📋
===============

Pydantic models for chat API request/response validation.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for chat endpoints."""

    message: str = Field(
        ..., description="The user's message or question", min_length=1, max_length=4000
    )
    session_id: Optional[str] = Field(
        None, description="Session ID for conversation history tracking"
    )
    source_id: Optional[str] = Field(
        None, description="Source ID for filtering by a specific file"
    )
    k: Optional[int] = Field(
        4, description="Number of context chunks to retrieve (1-10)", ge=1, le=10
    )
    use_history: Optional[bool] = Field(
        True, description="Whether to include conversation history in the prompt"
    )


class ChatResponse(BaseModel):
    """Response body for standard chat endpoint."""

    answer: str = Field(..., description="The AI-generated response")
    sources: List[str] = Field(
        default_factory=list,
        description="List of source documents used for the response",
    )
    session_id: Optional[str] = Field(None, description="Session ID for tracking")
    context_found: Optional[bool] = Field(
        None, description="Whether relevant context was found in the knowledgebase"
    )
    error: Optional[bool] = Field(None, description="True if an error occurred")


class ChatMessage(BaseModel):
    """A single message in conversation history."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="ISO timestamp of the message")


class ChatHistoryResponse(BaseModel):
    """Response body for history endpoint."""

    session_id: str = Field(..., description="Session identifier")
    history: List[ChatMessage] = Field(
        default_factory=list, description="List of conversation messages"
    )
    message_count: int = Field(0, description="Total number of messages in history")


class ClearHistoryResponse(BaseModel):
    """Response body for clear history endpoint."""

    success: bool = Field(..., description="Whether the operation was successful")
    session_id: str = Field(..., description="Session identifier")
    message: Optional[str] = Field(None, description="Status message")
