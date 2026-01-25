"""Pydantic schemas for extraction routes."""
from pydantic import BaseModel
from typing import List, Optional


class DocumentStatus(BaseModel):
    """Status of a single document extraction."""
    filename: str
    source_id: Optional[str] = None
    status: str
    error: Optional[str] = None


class ExtractionResponse(BaseModel):
    """Response model for document extraction endpoint."""
    session_id: str
    batch_mongo_id: Optional[str] = None
    processed_count: int
    documents: List[DocumentStatus]
