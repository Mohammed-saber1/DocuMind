"""
Configuration package for the Multi_docs application.
Contains settings, Redis setup, and other configuration utilities.
"""

from .settings import settings
from .redis import redis_client, REDIS_URL

__all__ = ["settings", "redis_client", "REDIS_URL"]
