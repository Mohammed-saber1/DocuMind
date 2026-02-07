"""
Services module for document extraction pipeline.

This module provides core services for the document extraction pipeline:

- db_service: MongoDB operations for storing extracted documents
- llm_service: LLM-powered document analysis and parsing
- memory_service: ChromaDB vector operations for RAG
- ocr_service: OCR text extraction from images
- rag_service: RAG chunking strategies
- vlm_service: Vision Language Model analysis (remote API)
- chat_service: Chat functionality with RAG and conversation history
"""

from services.cache_service import SemanticCache, get_cache
from services.chat_service import ChatService, get_chat_service
from services.db_service import get_db_client, save_batch_to_mongodb, save_to_mongodb
from services.llm_service import analyze_tables_with_llm, run_agent
from services.memory_service import check_hash_exists, index_chunks
from services.ocr_service import maybe_run_ocr, run_ocr_on_images, should_use_ocr
from services.rag_service import process_document_for_rag
from services.vlm_service import analyze_extracted_images, analyze_single_image

__all__ = [
    # Chat
    "ChatService",
    "get_chat_service",
    # Database
    "get_db_client",
    "save_to_mongodb",
    "save_batch_to_mongodb",
    # LLM
    "run_agent",
    "analyze_tables_with_llm",
    # Memory/Vector DB
    "index_chunks",
    "check_hash_exists",
    # OCR
    "run_ocr_on_images",
    "should_use_ocr",
    "maybe_run_ocr",
    # RAG
    "process_document_for_rag",
    # VLM
    "analyze_extracted_images",
    "analyze_single_image",
    # Cache
    "SemanticCache",
    "get_cache",
]
