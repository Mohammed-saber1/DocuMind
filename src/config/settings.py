"""
Application settings module.
Loads configuration from environment variables with sensible defaults.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """
    Centralized configuration settings for the application.
    All settings are loaded from environment variables with fallback defaults.
    """

    # Application
    APP_NAME: str = os.getenv("APP_NAME", "Saber Orbit")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")

    # MongoDB Configuration
    MONGO_URL: str = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
    MONGO_DB: str = os.getenv("MONGO_DB", "DocuMind")
    MONGO_COLLECTION: str = os.getenv("MONGO_COLLECTION", "Documents")

    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6380"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_USERNAME: Optional[str] = os.getenv("REDIS_USERNAME", None)
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    REDIS_SSL: bool = os.getenv("REDIS_SSL", "false").lower() == "true"

    # LLM Configuration (Ollama)
    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen2.5:1.5b")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")

    # Embedding Configuration
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

    # VLM Configuration (Remote VLLM)
    VLM_API_URL: str = os.getenv("VLM_API_URL", "http://192.168.1.127:8009/v1/chat/completions")
    VLM_TIMEOUT: int = int(os.getenv("VLM_TIMEOUT", "120"))

    # OCR Configuration
    OCR_ENABLED: bool = os.getenv("OCR_ENABLED", "true").lower() == "true"
    OCR_LANGUAGES: str = os.getenv("OCR_LANGUAGES", "en,ar")
    OCR_GPU: bool = os.getenv("OCR_GPU", "false").lower() == "true"

    # ChromaDB Configuration
    CHROMA_DB_DIR: str = os.getenv("CHROMA_DB_DIR", "assets/memories/chroma_db")

    # File Processing
    FILE_MAX_SIZE: int = int(os.getenv("FILE_MAX_SIZE", "104857600"))
    MAX_TEXT_LENGTH: int = int(os.getenv("MAX_TEXT_LENGTH", "50"))

    @property
    def redis_url(self) -> str:
        """Construct Redis URL from components."""
        if self.REDIS_USERNAME and self.REDIS_PASSWORD:
            return f"redis://{self.REDIS_USERNAME}:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


# Singleton instance
settings = Settings()
