import logging
import os
from typing import Any, Dict, List

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from core.config import get_settings

settings = get_settings()

# Configuration
CHROMA_DB_DIR = settings.chroma.db_dir

# Singleton cache for ChromaDB clients (performance optimization)
_chroma_cache = {}
_embeddings_instance = None


def get_embeddings():
    """Get or create singleton embeddings instance."""
    global _embeddings_instance
    if _embeddings_instance is None:
        from services.rag_service import get_embeddings as create_embeddings

        _embeddings_instance = create_embeddings()
    return _embeddings_instance


def get_chroma_client(collection_name: str = "global_memory"):
    """
    Get the ChromaDB client with persistence (singleton pattern for performance).
    Caches clients per collection name to avoid recreation overhead.
    """
    global _chroma_cache

    if collection_name not in _chroma_cache:
        import chromadb
        from langchain_chroma import Chroma

        embeddings = get_embeddings()
        os.makedirs(CHROMA_DB_DIR, exist_ok=True)

        # Explicitly create a persistent client
        persistent_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)

        _chroma_cache[collection_name] = Chroma(
            client=persistent_client,
            collection_name=collection_name,
            embedding_function=embeddings,
        )
        logger.info(f"Created ChromaDB client for collection: {collection_name}")

    return _chroma_cache[collection_name]


def index_chunks(
    chunks: List[str],
    metadata: List[Dict[str, Any]] = None,
    collection_name: str = "global_memory",
):
    """
    Index a list of text chunks into ChromaDB.
    """
    logger.info(
        f"Indexing {len(chunks)} chunks into ChromaDB collection: {collection_name}"
    )
    vectorstore = get_chroma_client(collection_name)

    # Safety: Truncate chunks that exceed embedding model's context length
    # nomic-embed-text has ~2048 token limit, ~6000 chars is safe buffer
    MAX_CHUNK_CHARS = 6000
    truncated_count = 0
    safe_chunks = []
    for chunk in chunks:
        if len(chunk) > MAX_CHUNK_CHARS:
            safe_chunks.append(chunk[:MAX_CHUNK_CHARS] + "...")
            truncated_count += 1
        else:
            safe_chunks.append(chunk)

    if truncated_count:
        logger.warning(
            f"Truncated {truncated_count} oversized chunks to prevent embedding overflow"
        )

    if metadata and len(metadata) == len(safe_chunks):
        vectorstore.add_texts(texts=safe_chunks, metadatas=metadata)
    else:
        vectorstore.add_texts(texts=safe_chunks)

    logger.info("Successfully indexed chunks.")


def search_similar_chunks(
    query: str,
    collection_name: str = "global_memory",
    k: int = 4,
    session_id: str = None,
    source_id: str = None,
):
    """
    Search for the most similar chunks to a query.
    Can be filtered by session_id and/or source_id.

    Args:
        query: Search query
        collection_name: ChromaDB collection name
        k: Number of results to return
        session_id: Filter by session_id (optional)
        source_id: Filter by source_id (optional)
    """
    logger.info(
        f"Searching for similar chunks to: '{query[:50]}...' (k={k}, session={session_id}, source={source_id})"
    )

    try:
        vectorstore = get_chroma_client(collection_name)

        search_kwargs = {"k": k}

        # Build filter dictionary
        filters = {}
        if session_id and source_id:
            # ChromaDB requires $and for multiple filters
            filters = {"$and": [{"session_id": session_id}, {"source_id": source_id}]}
            logger.info("Filtering by session_id AND source_id using $and")
        elif session_id:
            filters = {"session_id": session_id}
            logger.info(f"Filtering by session_id: {session_id}")
        elif source_id:
            filters = {"source_id": source_id}
            logger.info(f"Filtering by source_id: {source_id}")

        if filters:
            search_kwargs["filter"] = filters
        else:
            logger.info("No filters - searching ALL documents")

        results = vectorstore.similarity_search(query, **search_kwargs)

        # Log what we found
        for i, doc in enumerate(results):
            source = doc.metadata.get("source", "unknown")
            doc_session = doc.metadata.get("session_id", "none")
            doc_source_id = doc.metadata.get("source_id", "none")
            logger.info(
                f"  Result {i+1}: source={source}, session={doc_session}, source_id={doc_source_id}"
            )

        return results

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in search_similar_chunks: {error_msg}")

        # Retry mechanism for specific ChromaDB errors that might be fixed by client refresh
        if "Error finding id" in error_msg or "sqlite" in error_msg.lower():
            logger.warning(
                "Encountered potential stale connection/index error. Invaliding cache and retrying..."
            )

            # Invalidate cache for this collection
            global _chroma_cache
            if collection_name in _chroma_cache:
                del _chroma_cache[collection_name]

            # Retry once
            try:
                # Re-get client (will create new)
                vectorstore = get_chroma_client(collection_name)
                results = vectorstore.similarity_search(query, **search_kwargs)
                logger.info(f"Retry successful. Found {len(results)} results.")
                return results
            except Exception as retry_e:
                logger.error(f"Retry failed: {retry_e}")
                raise retry_e

        raise e


def check_hash_exists(
    file_hash: str, session_id: str = None, collection_name: str = "global_memory"
) -> bool:
    """
    Check if a file hash already exists in ChromaDB.

    Args:
        file_hash: The hash to check.
        session_id: If provided, checks if the hash exists IN THIS SESSION.
                    If None, checks if it exists GLOBALLY.
    """
    try:
        vectorstore = get_chroma_client(collection_name)

        where_filter = {"file_hash": file_hash}
        if session_id:
            where_filter = {
                "$and": [{"file_hash": file_hash}, {"session_id": session_id}]
            }

        results = vectorstore.get(where=where_filter, limit=1)
        exists = len(results.get("ids", [])) > 0

        if exists:
            scope = f"in session {session_id}" if session_id else "globally"
            logger.info(f"♻️ File hash {file_hash[:12]}... already exists {scope}")
        return exists
    except Exception as e:
        logger.warning(f"Error checking hash: {e}")
        return False


def get_chunks_by_hash(file_hash: str, collection_name: str = "global_memory") -> dict:
    """
    Retrieve UNIQUE chunks and metadata for a specific file hash from ChromaDB.
    Only returns chunks from the FIRST session that indexed this file to avoid duplicates.
    """
    try:
        vectorstore = get_chroma_client(collection_name)
        results = vectorstore.get(where={"file_hash": file_hash})

        if not results or not results.get("ids"):
            return None

        # Deduplicate: Get chunks from only ONE session (the first one found)
        all_metadata = results.get("metadatas", [])
        all_chunks = results.get("documents", [])
        all_ids = results.get("ids", [])

        if not all_metadata:
            return None

        # Find the first session_id
        first_session = all_metadata[0].get("session_id")

        # Filter to only chunks from that first session
        unique_chunks = []
        unique_metadata = []
        unique_ids = []

        for i, meta in enumerate(all_metadata):
            if meta.get("session_id") == first_session:
                unique_chunks.append(all_chunks[i])
                unique_metadata.append(meta)
                unique_ids.append(all_ids[i])

        logger.info(
            f"Found {len(all_chunks)} total chunks, returning {len(unique_chunks)} unique (from session {first_session})"
        )

        return {"chunks": unique_chunks, "metadata": unique_metadata, "ids": unique_ids}
    except Exception as e:
        logger.error(f"Error fetching chunks by hash: {e}")
        return None


def get_chunks_by_source_id(
    source_id: str, session_id: str = None, collection_name: str = "global_memory"
) -> dict:
    """
    Get all chunks for a specific source_id.

    Args:
        source_id: The unique source identifier for the file (e.g., filename__uuid)
        session_id: Optional session identifier for extra specificity
        collection_name: ChromaDB collection name
    """
    logger.info(
        f"Fetching all chunks for source_id: {source_id} (session={session_id})"
    )
    try:
        vectorstore = get_chroma_client(collection_name)

        # Build filter
        where_filter = {"source_id": source_id}
        if session_id:
            where_filter = {
                "$and": [{"session_id": session_id}, {"source_id": source_id}]
            }

        # Get all chunks with this filter
        results = vectorstore.get(where=where_filter)

        if not results or not results.get("ids"):
            logger.info(f"No chunks found for source_id: {source_id}")
            return {"chunks": [], "metadata": [], "total": 0}

        chunks = results.get("documents", [])
        metadata = results.get("metadatas", [])

        logger.info(f"Found {len(chunks)} chunks for source_id: {source_id}")

        return {"chunks": chunks, "metadata": metadata, "total": len(chunks)}
    except Exception as e:
        logger.error(f"Error fetching chunks for source_id {source_id}: {e}")
        return {"chunks": [], "metadata": [], "total": 0, "error": str(e)}


def delete_chunks_by_source(
    source_id: str, session_id: str, collection_name: str = "global_memory"
) -> dict:
    """
    Delete all chunks for a specific source_id and session_id from ChromaDB.
    """
    # Clean inputs to prevent whitespace/newline issues
    s_id = str(source_id).strip()
    sess_id = str(session_id).strip()

    logger.info(f"Deleting chunks for source_id: {s_id} (session={sess_id})")
    try:
        vectorstore = get_chroma_client(collection_name)

        where_filter = {"$and": [{"session_id": sess_id}, {"source_id": s_id}]}

        existing = vectorstore.get(where=where_filter)
        count = len(existing["ids"]) if existing and existing["ids"] else 0

        if count > 0:
            vectorstore.delete(where=where_filter)
            logger.info(f"Successfully deleted {count} chunks.")
            return {"success": True, "deleted_count": count}
        else:
            logger.warning(f"No chunks found to delete for {s_id} in session {sess_id}")
            return {"success": True, "deleted_count": 0, "message": "No chunks found"}

    except Exception as e:
        logger.error(f"Error deleting chunks: {e}")
        return {"success": False, "error": str(e)}


def delete_chunks_by_session(
    session_id: str, collection_name: str = "global_memory"
) -> dict:
    """
    Delete ALL chunks belonging to a specific session_id from ChromaDB.
    Use this for full session cleanup.
    """
    sess_id = str(session_id).strip()
    logger.warning(f"Deleting ALL chunks for session: {sess_id}")
    try:
        vectorstore = get_chroma_client(collection_name)

        where_filter = {"session_id": sess_id}

        existing = vectorstore.get(where=where_filter)
        count = len(existing["ids"]) if existing and existing["ids"] else 0

        if count > 0:
            vectorstore.delete(where=where_filter)
            logger.info(
                f"Successfully deleted all {count} chunks for session {sess_id}."
            )
            return {"success": True, "deleted_count": count}
        else:
            return {"success": True, "deleted_count": 0, "message": "Session empty"}

    except Exception as e:
        logger.error(f"Error deleting session chunks: {e}")
        return {"success": False, "error": str(e)}


def delete_collection(collection_name: str):
    """
    Delete a specific collection from ChromaDB.
    """
    logger.warning(f"Deleting collection: {collection_name}")
    vectorstore = get_chroma_client(collection_name)
    vectorstore.delete_collection()


def get_indexed_documents(collection_name: str = "global_memory") -> dict:
    """
    Get a summary of all indexed documents in ChromaDB.
    Useful for debugging which documents are available.
    """
    try:
        vectorstore = get_chroma_client(collection_name)
        # Get all documents
        all_data = vectorstore.get()

        if not all_data or not all_data.get("ids"):
            return {"total_chunks": 0, "documents": [], "sessions": []}

        # Extract unique documents and sessions
        documents = {}
        sessions = set()

        for i, metadata in enumerate(all_data.get("metadatas", [])):
            if metadata:
                doc_id = metadata.get("doc_id", "unknown")
                source = metadata.get("source", "unknown")
                session_id = metadata.get("session_id", "default")

                sessions.add(session_id)

                key = f"{source}:{doc_id}"
                if key not in documents:
                    documents[key] = {
                        "doc_id": doc_id,
                        "source": source,
                        "session_id": session_id,
                        "chunks": 0,
                    }
                documents[key]["chunks"] += 1

        return {
            "total_chunks": len(all_data.get("ids", [])),
            "documents": list(documents.values()),
            "sessions": list(sessions),
        }
    except Exception as e:
        logger.error(f"Error getting indexed documents: {e}")
        return {"error": str(e)}
