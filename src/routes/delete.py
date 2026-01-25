"""
Documents Management Routes 📄
==============================

API routes for managing indexed documents.

Endpoints:
- DELETE /api/v1/documents/  - Delete a document from ChromaDB and MongoDB
- GET /api/v1/documents/     - List all indexed documents
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

documents_router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
)


@documents_router.delete("/")
async def delete_document(
    session_id: str = Query(..., description="Session ID the document belongs to"),
    source_id: Optional[str] = Query(None, description="Unique source identifier (if None, deletes entire session)")
):
    """
    Delete a document (if source_id provided) or an ENTIRE session (if source_id is None).
    """
    from services.memory_service import delete_chunks_by_source, delete_chunks_by_session
    from services.db_service import delete_file_from_session, delete_full_session
    
    # Strip whitespace/newlines from IDs
    clean_session_id = session_id.strip()
    clean_source_id = source_id.strip() if source_id else None
    
    results = {
        "session_id": clean_session_id,
        "source_id": clean_source_id,
        "mode": "single_file" if clean_source_id else "full_session",
        "chromadb": None,
        "mongodb": None
    }
    
    if clean_source_id:
        # MODE 1: Delete a single file
        chroma_result = delete_chunks_by_source(source_id=clean_source_id, session_id=clean_session_id)
        mongo_result = delete_file_from_session(session_id=clean_session_id, source_id=clean_source_id)
    else:
        # MODE 2: Delete entire session
        chroma_result = delete_chunks_by_session(session_id=clean_session_id)
        mongo_result = delete_full_session(session_id=clean_session_id)
    
    results["chromadb"] = chroma_result
    results["mongodb"] = mongo_result
    
    # Success if either part succeeded (or reported 0 deleted which is still a clean state)
    results["success"] = chroma_result.get("success", False) and mongo_result.get("success", False)
    
    return results


@documents_router.get("/")
async def list_documents(session_id: Optional[str] = Query(None, description="Filter by session ID")):
    """
    List all indexed documents in ChromaDB.
    
    Args:
        session_id: Optional filter to show documents from a specific session only
        
    Returns:
        Summary of indexed documents with chunk counts
    """
    from services.memory_service import get_indexed_documents
    return get_indexed_documents()
