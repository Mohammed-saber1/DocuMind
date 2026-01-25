"""
Redis connection and client setup.
Provides a configured Redis client instance for the application.
"""

import redis
from .settings import settings


# Construct Redis URL from settings
REDIS_URL = settings.redis_url

# Create Redis client instance
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True,
    username=settings.REDIS_USERNAME,
    password=settings.REDIS_PASSWORD,
    ssl=settings.REDIS_SSL,
)


def test_connection() -> bool:
    """
    Test the Redis connection.
    
    Returns:
        bool: True if connection is successful, False otherwise.
    """
    try:
        redis_client.ping()
        return True
    except Exception:
        return False


if __name__ == "__main__":
    try:
        redis_client.ping()
        print("✅ Connected!")

        # Test full read/write
        redis_client.set('foo', 'bar')
        print(redis_client.get('foo'))  # Should print: bar
        redis_client.delete('foo')
        print("✅ All operations working!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
