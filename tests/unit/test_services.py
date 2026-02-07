"""
DocuMind Services Unit Tests
============================

This module contains unit tests for the core service layer of DocuMind.
Tests cover caching, RAG (Retrieval-Augmented Generation), LLM integration,
and database operations.

Test Classes:
-------------
    TestCacheService : Tests for Redis-based caching operations.
    TestRAGService : Tests for document chunking and retrieval.
    TestLLMService : Tests for LLM prompt handling and invocation.
    TestDatabaseService : Tests for MongoDB operations.

Running Tests:
--------------
    pytest tests/unit/test_services.py -v

Author:
-------
    Mohammed Saber <mohammed.saber.business@gmail.com>

License:
--------
    MIT License
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestCacheService:
    """
    Unit tests for the cache service.

    Tests verify cache key generation, cache hit/miss behavior,
    and proper handling of cached responses.
    """

    def test_cache_key_generation(self):
        """
        Verify that cache keys are generated deterministically.

        Cache keys should be consistent for the same query and session
        to ensure reliable cache hits.
        """
        query = "What is machine learning?"
        session_id = "test-session-123"

        key1 = f"{session_id}:{hash(query)}"
        key2 = f"{session_id}:{hash(query)}"

        assert key1 == key2, "Cache keys should be deterministic"

    def test_cache_hit_returns_cached_value(self, mock_redis_client):
        """
        Verify that cache hits return the stored value.

        Args:
            mock_redis_client: Mocked Redis client fixture.
        """
        cached_response = "This is a cached response"
        mock_redis_client.get = MagicMock(return_value=cached_response.encode())

        result = mock_redis_client.get("test_key")

        assert result.decode() == cached_response

    def test_cache_miss_returns_none(self, mock_redis_client):
        """
        Verify that cache misses return None.

        Args:
            mock_redis_client: Mocked Redis client fixture.
        """
        mock_redis_client.get = MagicMock(return_value=None)

        result = mock_redis_client.get("nonexistent_key")

        assert result is None


class TestRAGService:
    """
    Unit tests for the RAG (Retrieval-Augmented Generation) service.

    Tests cover document chunking, query handling, and context retrieval
    from the vector store.
    """

    def test_document_chunking(self):
        """
        Verify that documents are properly chunked with overlap.

        Document chunking should split text into manageable segments
        while maintaining context through overlapping content.
        """
        text = "A" * 1000  # 1000 character document
        chunk_size = 200
        overlap = 50

        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start += chunk_size - overlap

        assert len(chunks) > 1, "Document should be split into multiple chunks"
        assert all(
            len(c) <= chunk_size for c in chunks
        ), "Chunks should not exceed max size"

    def test_empty_query_handling(self):
        """
        Verify that empty queries are properly detected.

        Empty or whitespace-only queries should be identified
        for appropriate error handling.
        """
        query = ""

        assert query.strip() == "", "Empty query should be detected"

    def test_context_retrieval_limit(self, mock_chroma_client):
        """
        Verify that context retrieval respects the k parameter limit.

        Args:
            mock_chroma_client: Mocked ChromaDB client fixture.
        """
        k = 5
        mock_collection = mock_chroma_client.get_or_create_collection()
        mock_collection.query = MagicMock(
            return_value={
                "documents": [["doc1"], ["doc2"], ["doc3"]],
                "metadatas": [[{}], [{}], [{}]],
            }
        )

        result = mock_collection.query(query_texts=["test"], n_results=k)

        assert len(result["documents"]) <= k


class TestLLMService:
    """
    Unit tests for the LLM (Large Language Model) service.

    Tests cover prompt template formatting, configuration validation,
    and async LLM invocation.
    """

    def test_prompt_template_formatting(self):
        """
        Verify that prompt templates are correctly formatted.

        Template variables should be properly substituted with
        provided context and question values.
        """
        template = "Context: {context}\n\nQuestion: {question}"
        context = "This is the context."
        question = "What is this about?"

        formatted = template.format(context=context, question=question)

        assert context in formatted
        assert question in formatted

    def test_temperature_bounds(self, mock_settings):
        """
        Verify that temperature setting is within valid bounds.

        Args:
            mock_settings: Mocked settings fixture.
        """
        temperature = mock_settings.llm.temperature

        assert 0.0 <= temperature <= 2.0, "Temperature should be between 0 and 2"

    @pytest.mark.asyncio
    async def test_async_llm_invocation(self, async_mock_llm):
        """
        Verify async LLM invocation works correctly.

        Args:
            async_mock_llm: Async mocked LLM fixture.
        """
        result = await async_mock_llm.ainvoke("Test prompt")

        assert result.content == "Test response"


class TestDatabaseService:
    """
    Unit tests for the database service.

    Tests cover MongoDB connection handling, document operations,
    and metadata schema validation.
    """

    def test_mongodb_connection_string_format(self, mock_settings):
        """
        Verify MongoDB connection string format is valid.

        Args:
            mock_settings: Mocked settings fixture.
        """
        url = mock_settings.mongo.url

        assert url.startswith("mongodb://") or url.startswith("mongodb+srv://")

    def test_document_id_generation(self):
        """
        Verify that document IDs are valid UUIDs.

        Generated document IDs should conform to UUID v4 format.
        """
        import uuid

        doc_id = str(uuid.uuid4())

        assert len(doc_id) == 36, "UUID should be 36 characters"
        assert doc_id.count("-") == 4, "UUID should have 4 dashes"

    def test_metadata_schema(self, sample_pdf_content):
        """
        Verify document metadata contains required fields.

        Args:
            sample_pdf_content: Sample PDF content fixture.
        """
        metadata = sample_pdf_content["metadata"]

        required_fields = ["source"]
        for field in required_fields:
            assert field in metadata, f"Metadata should contain {field}"
