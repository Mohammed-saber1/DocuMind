"""
Semantic Cache Service 🚀
=========================

Redis-based semantic caching for RAG queries.
Caches both query embeddings and full responses to reduce latency.

Key features:
- Exact match caching (hash-based)
- Semantic similarity caching (embedding-based) 
- Configurable TTL and similarity thresholds
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import redis

from core.config import get_settings

logger = logging.getLogger(__name__)

# Singleton cache instance
_cache_instance: Optional["SemanticCache"] = None


class SemanticCache:
    """
    Semantic caching layer for RAG queries.

    Supports two caching strategies:
    1. Exact match: Hash-based lookup for identical queries
    2. Semantic similarity: Embedding-based lookup for similar queries
    """

    def __init__(self):
        settings = get_settings()
        self.redis = redis.from_url(settings.redis.url)
        self.similarity_threshold = 0.92  # Cosine similarity threshold
        self.response_ttl = 3600  # 1 hour for responses
        self.embedding_ttl = 86400  # 24 hours for embeddings
        self.enabled = self._check_connection()

    def _check_connection(self) -> bool:
        """Check if Redis is available."""
        try:
            self.redis.ping()
            logger.info("✅ Redis cache connected successfully")
            return True
        except redis.ConnectionError as e:
            logger.warning(f"⚠️ Redis not available, caching disabled: {e}")
            return False

    def _hash_query(self, query: str) -> str:
        """Create a hash of the query for exact match lookup."""
        normalized = query.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _cache_key(self, query_hash: str, source_id: Optional[str] = None) -> str:
        """Generate cache key for a query."""
        key = f"rag:response:{query_hash}"
        if source_id:
            key += f":{source_id}"
        return key

    def _embedding_key(self, query_hash: str) -> str:
        """Generate cache key for query embedding."""
        return f"rag:embedding:{query_hash}"

    # ==================== Exact Match Caching ====================

    def get_cached_response(
        self, query: str, source_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response for exact query match.

        Args:
            query: The user's query
            source_id: Optional filter for specific document

        Returns:
            Cached response dict or None
        """
        if not self.enabled:
            return None

        try:
            query_hash = self._hash_query(query)
            cache_key = self._cache_key(query_hash, source_id)

            cached = self.redis.get(cache_key)
            if cached:
                response = json.loads(cached)
                logger.info(f"🎯 Cache HIT for query: '{query[:50]}...'")
                response["_cached"] = True
                response["_cache_key"] = cache_key
                return response

            return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def cache_response(
        self,
        query: str,
        response: Dict[str, Any],
        source_id: Optional[str] = None,
        query_embedding: Optional[List[float]] = None,
    ) -> bool:
        """
        Cache a response for future queries.

        Args:
            query: The user's query
            response: The response to cache
            source_id: Optional filter for specific document
            query_embedding: Optional embedding vector for semantic matching

        Returns:
            True if cached successfully
        """
        if not self.enabled:
            return False

        try:
            query_hash = self._hash_query(query)
            cache_key = self._cache_key(query_hash, source_id)

            # Add metadata
            cache_data = {
                **response,
                "_cached_at": datetime.utcnow().isoformat(),
                "_query_hash": query_hash,
            }

            # Remove internal fields that shouldn't be cached
            cache_data.pop("_cached", None)
            cache_data.pop("_cache_key", None)

            # Cache the response
            self.redis.setex(cache_key, self.response_ttl, json.dumps(cache_data))

            # Also cache the embedding if provided (for semantic matching)
            if query_embedding:
                embedding_key = self._embedding_key(query_hash)
                self.redis.setex(
                    embedding_key,
                    self.embedding_ttl,
                    json.dumps(
                        {"embedding": query_embedding, "response_key": cache_key}
                    ),
                )

            logger.info(f"💾 Cached response for: '{query[:50]}...'")
            return True

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    # ==================== Semantic Similarity Caching ====================

    def get_similar_cached_response(
        self,
        query_embedding: List[float],
        source_id: Optional[str] = None,
        max_candidates: int = 100,
    ) -> Optional[Dict[str, Any]]:
        """
        Find cached response for semantically similar query.

        This is more expensive than exact match but catches
        paraphrased queries like:
        - "What is DocuMind?"
        - "Tell me about DocuMind"
        - "Explain what DocuMind does"

        Args:
            query_embedding: The embedding vector for the current query
            source_id: Optional filter for specific document
            max_candidates: Maximum cached embeddings to compare

        Returns:
            Cached response if similarity > threshold, else None
        """
        if not self.enabled:
            return None

        try:
            # Get all cached embedding keys
            pattern = "rag:embedding:*"
            cursor = 0
            candidates = []

            while True:
                cursor, keys = self.redis.scan(cursor, match=pattern, count=100)
                for key in keys:
                    if len(candidates) >= max_candidates:
                        break
                    candidates.append(key)
                if cursor == 0 or len(candidates) >= max_candidates:
                    break

            if not candidates:
                return None

            # Find most similar cached embedding
            query_vec = np.array(query_embedding)
            best_similarity = 0.0
            best_response_key = None

            for embedding_key in candidates:
                try:
                    cached_data = self.redis.get(embedding_key)
                    if not cached_data:
                        continue

                    data = json.loads(cached_data)
                    cached_embedding = np.array(data["embedding"])
                    response_key = data["response_key"]

                    # Cosine similarity
                    similarity = np.dot(query_vec, cached_embedding) / (
                        np.linalg.norm(query_vec) * np.linalg.norm(cached_embedding)
                    )

                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_response_key = response_key

                except Exception:
                    continue

            # Check if best match exceeds threshold
            if best_similarity >= self.similarity_threshold and best_response_key:
                # Check source_id filter if provided
                if source_id and f":{source_id}" not in best_response_key:
                    return None

                cached_response = self.redis.get(best_response_key)
                if cached_response:
                    response = json.loads(cached_response)
                    logger.info(
                        f"🎯 Semantic cache HIT (similarity: {best_similarity:.3f})"
                    )
                    response["_cached"] = True
                    response["_semantic_match"] = True
                    response["_similarity"] = float(best_similarity)
                    return response

            return None

        except Exception as e:
            logger.error(f"Semantic cache lookup error: {e}")
            return None

    # ==================== Cache Management ====================

    def invalidate_by_source(self, source_id: str) -> int:
        """
        Invalidate all cached responses for a specific source.
        Call this when a document is updated or deleted.

        Args:
            source_id: The source identifier

        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0

        try:
            pattern = f"rag:response:*:{source_id}"
            keys = list(self.redis.scan_iter(match=pattern))
            if keys:
                deleted = self.redis.delete(*keys)
                logger.info(
                    f"🗑️ Invalidated {deleted} cached responses for source: {source_id}"
                )
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return 0

    def clear_all(self) -> int:
        """
        Clear all RAG cache entries.

        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0

        try:
            patterns = ["rag:response:*", "rag:embedding:*"]
            total_deleted = 0

            for pattern in patterns:
                keys = list(self.redis.scan_iter(match=pattern))
                if keys:
                    total_deleted += self.redis.delete(*keys)

            logger.info(f"🗑️ Cleared {total_deleted} cache entries")
            return total_deleted
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.enabled:
            return {"enabled": False}

        try:
            response_keys = list(self.redis.scan_iter(match="rag:response:*"))
            embedding_keys = list(self.redis.scan_iter(match="rag:embedding:*"))

            return {
                "enabled": True,
                "cached_responses": len(response_keys),
                "cached_embeddings": len(embedding_keys),
                "response_ttl_seconds": self.response_ttl,
                "embedding_ttl_seconds": self.embedding_ttl,
                "similarity_threshold": self.similarity_threshold,
            }
        except Exception as e:
            return {"enabled": True, "error": str(e)}


def get_cache() -> SemanticCache:
    """Get or create the SemanticCache singleton."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SemanticCache()
    return _cache_instance
