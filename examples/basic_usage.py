"""
DocuMind API Usage Example
==========================

This script demonstrates the fundamental operations available through the
DocuMind REST API, providing working examples for common integration scenarios.

Operations Demonstrated:
------------------------
    1. Document Upload: Submit files for processing.
    2. URL Processing: Scrape and index web content.
    3. Chat Query: Query indexed documents using natural language.
    4. Streaming Response: Receive real-time chat responses via SSE.
    5. Document Listing: Retrieve processed document metadata.

Prerequisites:
--------------
    - DocuMind API server running on localhost:8000
    - Python requests library: pip install requests

Configuration:
--------------
    Modify API_BASE_URL and SESSION_ID constants as needed.

Usage:
------
    python examples/basic_usage.py

    Uncomment the example sections within main() to test specific
    functionality with real files or URLs.

Author:
-------
    Mohammed Saber <mohammed.saber.business@gmail.com>

License:
--------
    MIT License
"""
import requests
import time
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
SESSION_ID = "example-session-001"


def upload_document(file_path: str) -> dict:
    """
    Upload a document file for processing.
    
    Submits a document to the extraction endpoint for processing.
    The document will be parsed, analyzed, and indexed for later retrieval.
    
    Args:
        file_path: Path to the document file to upload.
    
    Returns:
        dict: API response containing task_id and processing status.
    
    Raises:
        requests.RequestException: If the API request fails.
    
    Example:
        >>> result = upload_document("path/to/document.pdf")
        >>> print(result["task_id"])
    """
    url = f"{API_BASE_URL}/api/v1/extract"
    
    with open(file_path, "rb") as f:
        files = {"file": (Path(file_path).name, f)}
        data = {
            "session_id": SESSION_ID,
            "author": "Example Author",
            "description": "Example document for testing"
        }
        response = requests.post(url, files=files, data=data)
    
    return response.json()


def upload_url(url_to_process: str) -> dict:
    """
    Submit a URL for scraping and processing.
    
    The URL content will be scraped, parsed, and indexed for retrieval.
    Supports regular web pages and YouTube video URLs.
    
    Args:
        url_to_process: The URL to scrape and process.
    
    Returns:
        dict: API response containing task_id and processing status.
    
    Raises:
        requests.RequestException: If the API request fails.
    
    Example:
        >>> result = upload_url("https://example.com/article")
        >>> print(result["status"])
    """
    url = f"{API_BASE_URL}/api/v1/extract"
    
    data = {
        "url": url_to_process,
        "session_id": SESSION_ID,
        "description": "Web content"
    }
    response = requests.post(url, json=data)
    
    return response.json()


def chat_query(query: str) -> dict:
    """
    Query processed documents using natural language.
    
    Sends a question to the chat endpoint, which retrieves relevant
    context from indexed documents and generates a response.
    
    Args:
        query: Natural language question to ask.
    
    Returns:
        dict: Response containing answer, sources, and cache status.
    
    Raises:
        requests.RequestException: If the API request fails.
    
    Example:
        >>> result = chat_query("What are the main topics covered?")
        >>> print(result["answer"])
    """
    url = f"{API_BASE_URL}/api/v1/chat"
    
    data = {
        "query": query,
        "session_id": SESSION_ID,
        "k": 5  # Number of context chunks to retrieve
    }
    response = requests.post(url, json=data)
    
    return response.json()


def chat_stream(query: str) -> None:
    """
    Stream a chat response using Server-Sent Events.
    
    Initiates a streaming chat request and prints tokens as they
    are received, providing real-time response feedback.
    
    Args:
        query: Natural language question to ask.
    
    Raises:
        requests.RequestException: If the API request fails.
    
    Example:
        >>> chat_stream("Summarize the document")
        The document covers...
    """
    url = f"{API_BASE_URL}/api/v1/chat/stream"
    
    data = {
        "query": query,
        "session_id": SESSION_ID
    }
    
    with requests.post(url, json=data, stream=True) as response:
        for line in response.iter_lines():
            if line:
                print(line.decode('utf-8'))


def list_documents() -> dict:
    """
    List all processed documents for the current session.
    
    Retrieves metadata for all documents that have been processed
    and indexed under the current session ID.
    
    Returns:
        dict: Response containing list of documents and total count.
    
    Raises:
        requests.RequestException: If the API request fails.
    
    Example:
        >>> result = list_documents()
        >>> for doc in result["documents"]:
        ...     print(doc["filename"])
    """
    url = f"{API_BASE_URL}/api/v1/documents"
    params = {"session_id": SESSION_ID}
    
    response = requests.get(url, params=params)
    return response.json()


def main():
    """
    Execute example API operations.
    
    Demonstrates the basic workflow of uploading documents,
    waiting for processing, and querying the indexed content.
    
    Uncomment specific sections to test with real files or URLs.
    """
    print("=" * 60)
    print("DocuMind API Usage Example")
    print("=" * 60)
    
    # Example 1: Upload a PDF document
    print("\n1. Document Upload")
    print("-" * 40)
    # Uncomment and modify the path to test:
    # result = upload_document("path/to/your/document.pdf")
    # print(f"   Task ID: {result.get('task_id')}")
    print("   [Skipped - Uncomment to test with real file]")
    
    # Example 2: Process a URL
    print("\n2. URL Processing")
    print("-" * 40)
    # Uncomment to test:
    # result = upload_url("https://example.com/article")
    # print(f"   Status: {result.get('status')}")
    print("   [Skipped - Uncomment to test]")
    
    # Example 3: Wait for processing
    print("\n3. Processing Delay")
    print("-" * 40)
    print("   Waiting for document processing...")
    time.sleep(2)
    
    # Example 4: Chat query
    print("\n4. Document Query")
    print("-" * 40)
    # Uncomment to test:
    # result = chat_query("What is this document about?")
    # print(f"   Answer: {result.get('answer', 'No answer')}")
    print("   [Skipped - Uncomment to test]")
    
    # Example 5: List documents
    print("\n5. Document Listing")
    print("-" * 40)
    # Uncomment to test:
    # result = list_documents()
    # print(f"   Total documents: {result.get('total', 0)}")
    print("   [Skipped - Uncomment to test]")
    
    print("\n" + "=" * 60)
    print("Example complete. Uncomment sections to test functionality.")
    print("=" * 60)


if __name__ == "__main__":
    main()
