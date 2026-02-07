"""
DocuMind Test Suite Configuration
=================================

This module provides shared pytest fixtures and configuration for the DocuMind
test suite. It includes mock objects for external dependencies (MongoDB, Redis,
ChromaDB) and sample data fixtures for testing document processing pipelines.

Fixtures:
---------
    mock_settings : MagicMock
        Mock application configuration settings.
    mock_mongo_client : MagicMock
        Mock MongoDB client for database operations.
    mock_redis_client : MagicMock
        Mock Redis client for caching operations.
    mock_chroma_client : MagicMock
        Mock ChromaDB client for vector store operations.
    sample_pdf_content : dict
        Sample extracted PDF content for testing.
    sample_chat_messages : list
        Sample chat message history for testing.
    mock_llm_response : MagicMock
        Mock LLM response object.
    async_mock_llm : AsyncMock
        Async mock for LLM service testing.

Usage:
------
    Fixtures are automatically available in test functions:
    
    def test_example(mock_settings, mock_redis_client):
        assert mock_settings.app_name == "DocuMind"
        assert mock_redis_client.ping() == True

Author:
-------
    Mohammed Saber <mohammed.saber.business@gmail.com>

License:
--------
    MIT License
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def mock_settings():
    """
    Create mock application settings.
    
    Returns:
        MagicMock: Mock settings object with default test configuration.
    """
    settings = MagicMock()
    settings.app_name = "DocuMind"
    settings.app_version = "1.0.0"
    settings.mongo.url = "mongodb://localhost:27017"
    settings.mongo.db_name = "documind_test"
    settings.redis.host = "localhost"
    settings.redis.port = 6379
    settings.llm.model = "test-model"
    settings.llm.temperature = 0.7
    return settings


@pytest.fixture
def mock_mongo_client():
    """
    Create mock MongoDB client.
    
    Returns:
        MagicMock: Mock MongoDB client with basic operations mocked.
    """
    client = MagicMock()
    client.server_info = MagicMock(return_value={"version": "6.0.0"})
    return client


@pytest.fixture
def mock_redis_client():
    """
    Create mock Redis client.
    
    Returns:
        MagicMock: Mock Redis client with get/set operations mocked.
    """
    client = MagicMock()
    client.ping = MagicMock(return_value=True)
    client.get = MagicMock(return_value=None)
    client.set = MagicMock(return_value=True)
    return client


@pytest.fixture
def mock_chroma_client():
    """
    Create mock ChromaDB client.
    
    Returns:
        MagicMock: Mock ChromaDB client with collection operations mocked.
    """
    client = MagicMock()
    collection = MagicMock()
    collection.add = MagicMock()
    collection.query = MagicMock(return_value={"documents": [], "metadatas": []})
    client.get_or_create_collection = MagicMock(return_value=collection)
    return client


@pytest.fixture
def sample_pdf_content():
    """
    Provide sample extracted PDF content.
    
    Returns:
        dict: Sample PDF content with text and metadata.
    """
    return {
        "text": "This is sample document content for testing purposes.",
        "metadata": {
            "source": "test.pdf",
            "pages": 1,
            "author": "Test Author"
        }
    }


@pytest.fixture
def sample_chat_messages():
    """
    Provide sample chat message history.
    
    Returns:
        list: List of message dictionaries with role and content.
    """
    return [
        {"role": "user", "content": "What is this document about?"},
        {"role": "assistant", "content": "This document is about testing."}
    ]


@pytest.fixture
def mock_llm_response():
    """
    Create mock LLM response.
    
    Returns:
        MagicMock: Mock response object with content attribute.
    """
    response = MagicMock()
    response.content = "This is a test response from the LLM."
    return response


@pytest.fixture
async def async_mock_llm():
    """
    Create async mock for LLM service.
    
    Returns:
        AsyncMock: Async mock with ainvoke method mocked.
    """
    mock = AsyncMock()
    mock.ainvoke = AsyncMock(return_value=MagicMock(content="Test response"))
    return mock
