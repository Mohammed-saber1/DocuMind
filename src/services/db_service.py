"""
Database Service (MongoDB) 💾
============================

This service abstracts all interactions with the MongoDB database.
It handles connection management, document insertion, and batch updates.

Key Concepts:
-------------
- **Session ID**: Used as the primary key/ID for batch documents.
- **Documents**: Individual parsed files are stored inside a 'files' array within the batch document.
- **Persistence**: Data is persistent across server restarts.

Configuration:
--------------
Controlled via environment variables:
- `MONGO_URL`: Connection string.
- `MONGO_DB`: Database name.
- `MONGO_COLLECTION`: Collection name.

"""

import json
import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

# MongoDB Configuration
from core.config import get_settings


# MongoDB Configuration
def get_mongo_config():
    settings = get_settings()
    return settings.mongo


MONGO_URL = get_settings().mongo.connection_url
MONGO_DB = get_settings().mongo.db_name
MONGO_COLLECTION = get_settings().mongo.collection

# Global client
_client = None


def get_db_client():
    """
    Get or initialize the MongoDB client.

    This implements a singleton-like pattern to reuse the database connection
    across the application lifecycle.

    Returns:
        MongoClient | None: The active client instance or None if connection fails.
    """
    global _client
    if _client is None:
        try:
            _client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            # Trigger a connection to verify
            _client.admin.command("ping")
            print("✅ Connected to MongoDB")
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            return None
    return _client


def save_to_mongodb(json_path: str, session_id: str = None):
    """
    Read a structured JSON result and save it to MongoDB.
    """
    if not os.path.exists(json_path):
        return None

    client = get_db_client()
    if not client:
        return None

    try:
        # Load the data first to get author or other metadata
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # If session_id is provided, delegate to the batch saver to handle appending
        if session_id:
            # Try to get author from the document, fallback to metadata or "Unknown"
            author = data.get("metadata", {}).get("author", "Unknown")
            if not author or author == "Unknown":
                author = data.get("author", "Unknown")

            return save_batch_to_mongodb([json_path], session_id, author)

        # Legacy behavior for non-session saves (stand-alone documents)
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        result = collection.insert_one(data)

        print(
            f"📥 Successfully saved extraction to MongoDB: {result.inserted_id} (Session: None)"
        )
        return str(result.inserted_id)
    except Exception as e:
        print(f"❌ Error saving to MongoDB: {e}")
        return None


def save_batch_to_mongodb(json_paths: list, session_id: str, author: str):
    """
    Read multiple structured JSON results and save them as a single document.
    Uses session_id as the document _id.
    If session_id exists, it appends to the 'files' array.
    """
    from datetime import datetime

    client = get_db_client()
    if not client:
        return None

    batch_files = []
    for path in json_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                batch_files.append(json.load(f))
        except Exception as e:
            print(f"⚠️ Failed to read {path} for batch: {e}")

    if not batch_files:
        return None

    db = client[MONGO_DB]
    collection = db[MONGO_COLLECTION]

    try:
        # Use session_id as _id (document name)
        result = collection.update_one(
            {"_id": session_id},  # Use session_id as _id
            {
                "$set": {"author": author, "last_updated": datetime.now().isoformat()},
                "$setOnInsert": {
                    "session_id": session_id,  # Keep for backwards compatibility
                    "timestamp": datetime.now().isoformat(),
                },
                "$push": {"files": {"$each": batch_files}},
                "$inc": {"files_count": len(batch_files)},
            },
            upsert=True,
        )

        print(
            f"📥 Successfully {'updated' if result.matched_count else 'created'} batch {session_id} to MongoDB"
        )
        return session_id  # Return session_id as the document ID
    except Exception as e:
        print(f"❌ MongoDB Batch error: {e}")
        return None


def delete_file_from_session(session_id: str, source_id: str) -> dict:
    """
    Delete a specific file from a session's files array in MongoDB.
    """
    client = get_db_client()
    if not client:
        return {"success": False, "error": "MongoDB connection failed"}

    # Clean inputs
    sess_id = str(session_id).strip()
    s_id = str(source_id).strip()

    try:
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]

        # Remove the file from the files array where doc_id matches source_id
        result = collection.update_one(
            {"_id": sess_id},
            {"$pull": {"files": {"doc_id": s_id}}, "$inc": {"files_count": -1}},
        )

        if result.matched_count == 0:
            return {"success": False, "error": f"Session '{sess_id}' not found"}

        if result.modified_count == 0:
            return {
                "success": True,
                "deleted_count": 0,
                "message": "File not found in session",
            }

        print(f"🗑️ Deleted file {s_id} from session {sess_id}")
        return {
            "success": True,
            "deleted_count": 1,
            "session_id": sess_id,
            "source_id": s_id,
        }

    except Exception as e:
        print(f"❌ MongoDB delete error: {e}")
        return {"success": False, "deleted_count": 0, "error": str(e)}


def delete_full_session(session_id: str) -> dict:
    """
    Delete an entire session document from MongoDB.
    """
    client = get_db_client()
    if not client:
        return {"success": False, "error": "MongoDB connection failed"}

    sess_id = str(session_id).strip()

    def logger_print(x):
        print(f"🗑️ MongoDB Session Cleanup: {x}")

    try:
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]

        result = collection.delete_one({"_id": sess_id})

        if result.deleted_count > 0:
            logger_print(f"Successfully deleted session {sess_id}")
            return {"success": True, "deleted_count": result.deleted_count}
        else:
            return {
                "success": False,
                "error": f"Session {sess_id} not found",
                "deleted_count": 0,
            }

    except Exception as e:
        logger_print(f"Error deleting session {sess_id}: {e}")
        return {"success": False, "error": str(e)}


# ==================== Chat History MongoDB Functions ====================

CHAT_COLLECTION = "chat_history"


def save_chat_message(session_id: str, role: str, content: str) -> bool:
    """
    Save a chat message to MongoDB.
    Uses session_id as the document _id.

    Args:
        session_id: The session identifier (used as _id)
        role: 'user' or 'assistant'
        content: The message content

    Returns:
        True if successful, False otherwise
    """
    from datetime import datetime

    client = get_db_client()
    if not client:
        return False

    try:
        db = client[MONGO_DB]
        collection = db[CHAT_COLLECTION]

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }

        # Upsert: Create document with session_id as _id, or push to existing
        collection.update_one(
            {"_id": session_id},
            {
                "$setOnInsert": {"created_at": datetime.now().isoformat()},
                "$set": {"last_updated": datetime.now().isoformat()},
                "$push": {"messages": message},
                "$inc": {"message_count": 1},
            },
            upsert=True,
        )

        return True
    except Exception as e:
        print(f"❌ Error saving chat message: {e}")
        return False


def get_chat_history_from_db(session_id: str, limit: int = 20) -> list:
    """
    Get chat history from MongoDB for a session.

    Args:
        session_id: The session identifier
        limit: Maximum number of messages to return (most recent)

    Returns:
        List of message dictionaries
    """
    client = get_db_client()
    if not client:
        return []

    try:
        db = client[MONGO_DB]
        collection = db[CHAT_COLLECTION]

        doc = collection.find_one({"_id": session_id})

        if not doc or "messages" not in doc:
            return []

        messages = doc["messages"]

        # Return last N messages
        if limit and len(messages) > limit:
            return messages[-limit:]

        return messages
    except Exception as e:
        print(f"❌ Error getting chat history: {e}")
        return []


def clear_chat_history_from_db(session_id: str) -> bool:
    """
    Clear chat history for a session from MongoDB.

    Args:
        session_id: The session identifier

    Returns:
        True if successful, False otherwise
    """
    client = get_db_client()
    if not client:
        return False

    try:
        db = client[MONGO_DB]
        collection = db[CHAT_COLLECTION]

        result = collection.delete_one({"_id": session_id})

        return result.deleted_count > 0
    except Exception as e:
        print(f"❌ Error clearing chat history: {e}")
        return False


def get_all_chat_sessions() -> list:
    """
    Get all chat sessions from MongoDB.

    Returns:
        List of session summaries
    """
    client = get_db_client()
    if not client:
        return []

    try:
        db = client[MONGO_DB]
        collection = db[CHAT_COLLECTION]

        sessions = []
        for doc in collection.find(
            {}, {"_id": 1, "message_count": 1, "created_at": 1, "last_updated": 1}
        ):
            sessions.append(
                {
                    "session_id": doc["_id"],
                    "message_count": doc.get("message_count", 0),
                    "created_at": doc.get("created_at"),
                    "last_updated": doc.get("last_updated"),
                }
            )

        return sessions
    except Exception as e:
        print(f"❌ Error getting chat sessions: {e}")
        return []


def get_document_by_hash(file_hash: str):
    """
    Find an existing document in MongoDB by its file hash.
    Used to recover parsed data without re-running the pipeline.
    """
    client = get_db_client()
    if not client:
        return None

    try:
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]

        # Search for the hash anywhere in the 'files' array across all sessions
        doc = collection.find_one({"files.file_hash": file_hash}, {"files.$": 1})

        if doc and "files" in doc and len(doc["files"]) > 0:
            return doc["files"][0]

        return None
    except Exception as e:
        print(f"❌ Error finding doc by hash: {e}")
        return None


if __name__ == "__main__":
    # Quick test if run directly
    print("🔍 Testing MongoDB Service...")
    print(f"   Configured URL: {MONGO_URL}")
    print(f"   Target DB: {MONGO_DB}")
    print(f"   Collection: {MONGO_COLLECTION}")

    client = get_db_client()
    if client:
        print("✅ MongoDB connection test PASSED")
    else:
        print("❌ MongoDB connection test FAILED")
