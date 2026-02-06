"""
DocuMind API Service 🔌
========================

Backend API integration layer for the Streamlit frontend.
Handles all communication with the FastAPI backend.
"""
import requests
import json
from typing import List, Optional, Generator, Dict, Any
from config import (
    EXTRACTION_ENDPOINT,
    CHAT_ENDPOINT,
    CHAT_STREAM_ENDPOINT,
    DEFAULT_OCR_VLM,
    DEFAULT_K
)


def submit_extraction(
    files: List[Any],
    links: List[str],
    session_id: str,
    author: str,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Submit documents for extraction to the backend.
    
    Args:
        files: List of uploaded file objects from Streamlit
        links: List of URLs (website or YouTube)
        session_id: Auto-generated session identifier
        author: Author name (required)
        description: Optional document description
        
    Returns:
        API response dict with status, task_id, session_id, message
    """
    try:
        # Prepare multipart form data
        form_data = {
            "session_id": session_id,
            "author": author,
            "use_ocr_vlm": str(DEFAULT_OCR_VLM).lower(),
        }
        
        if description:
            form_data["user_description"] = description
            
        # Add links if provided
        files_to_upload = []
        
        if links:
            for link in links:
                form_data[f"links"] = links
                
        # Prepare files for upload
        if files:
            for file in files:
                files_to_upload.append(
                    ("files", (file.name, file.getvalue(), file.type or "application/octet-stream"))
                )
        
        # Make the request
        if files_to_upload:
            response = requests.post(
                EXTRACTION_ENDPOINT,
                data=form_data,
                files=files_to_upload,
                timeout=60
            )
        else:
            # URL-only submission
            response = requests.post(
                EXTRACTION_ENDPOINT,
                data=form_data,
                timeout=60
            )
            
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        return {"error": True, "message": str(e)}


def send_chat_message(
    message: str,
    session_id: str,
    k: int = DEFAULT_K,
    use_history: bool = True
) -> Dict[str, Any]:
    """
    Send a chat message to the backend.
    
    Args:
        message: User's question/message
        session_id: Session identifier for context
        k: Number of context chunks to retrieve
        use_history: Whether to include conversation history
        
    Returns:
        API response with answer, sources, etc.
    """
    try:
        payload = {
            "message": message,
            "session_id": session_id,
            "k": k,
            "use_history": use_history
        }
        
        response = requests.post(
            CHAT_ENDPOINT,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        return {"error": True, "answer": f"Error: {str(e)}"}


def stream_chat_response(
    message: str,
    session_id: str,
    k: int = DEFAULT_K,
    use_history: bool = True
) -> Generator[str, None, None]:
    """
    Stream a chat response using Server-Sent Events.
    
    Args:
        message: User's question/message
        session_id: Session identifier for context
        k: Number of context chunks to retrieve
        use_history: Whether to include conversation history
        
    Yields:
        Response tokens as they arrive
    """
    try:
        payload = {
            "message": message,
            "session_id": session_id,
            "k": k,
            "use_history": use_history
        }
        
        with requests.post(
            CHAT_STREAM_ENDPOINT,
            json=payload,
            stream=True,
            timeout=120
        ) as response:
            response.raise_for_status()
            
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    # SSE format: "data: <content>"
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        if data == "[DONE]":
                            break
                        yield data
                        
    except requests.exceptions.RequestException as e:
        yield f"Error: {str(e)}"


def check_backend_health() -> bool:
    """
    Check if the backend API is reachable.
    
    Returns:
        True if backend is healthy, False otherwise
    """
    try:
        response = requests.get(
            f"{EXTRACTION_ENDPOINT.rsplit('/', 2)[0]}/health",
            timeout=5
        )
        return response.status_code == 200
    except:
        return False
