"""
Centralized configuration using Pydantic Settings.

Organized into nested models for better structure and type safety.
"""
from typing import List
from functools import lru_cache
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisSettings(BaseModel):
    host: str = "localhost"
    port: int = 6380
    db: int = 0
    username: str | None = None
    password: str | None = None
    ssl: bool = False

    @property
    def url(self) -> str:
        if self.username and self.password:
            return f"redis://{self.username}:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class MongoSettings(BaseModel):
    url: str = "mongodb://localhost:27017/"
    db_name: str = "DocuMind"
    collection: str = "Documents"
    username: str | None = None
    password: str | None = None
    authentication_source: str = "admin"

    @property
    def connection_url(self) -> str:
        """
        Constructs the connection URL with credentials if provided.
        """
        if self.username and self.password:
            # Parse the base URL to insert credentials
            # Assuming format: mongodb://host:port/ or mongodb://host:port
            base = self.url.replace("mongodb://", "")
            if base.endswith("/"):
                base = base[:-1]
            
            return f"mongodb://{self.username}:{self.password}@{base}/?authSource={self.authentication_source}"
        return self.url


class LLMSettings(BaseModel):
    model: str = "qwen2.5:1.5b"
    embedding_model: str = "nomic-embed-text"
    temperature: float = 0.0
    base_url: str = "http://localhost:11434"
    embedding_base_url: str = "http://localhost:11434"
    provider: str = "ollama"  # "ollama", "mistral", "openai"
    api_key: str = ""
    api_url: str = ""
    provider: str = "ollama"  # "ollama", "mistral", "openai"
    api_key: str = ""
    api_url: str = ""


class VLMSettings(BaseModel):
    provider: str = "mistral"  # "mistral" or "local"
    model: str = "mistral-large-2512"
    api_key: str = ""
    api_url: str = "https://api.mistral.ai/v1/chat/completions"
    timeout: int = 120


class OCRSettings(BaseModel):
    enabled: bool = True
    languages: str = "en,ar"
    gpu: bool = True

    @property
    def languages_list(self) -> List[str]:
        return [lang.strip() for lang in self.languages.split(",")]


class ChromaSettings(BaseModel):
    db_dir: str = "assets/memories/chroma_db"


class LlamaCloudSettings(BaseModel):
    """Settings for LlamaCloud/LlamaParse document parsing."""
    api_key: str = ""
    timeout: int = 300  # 5 minutes per document
    enabled: bool = True  # Enable LlamaParse for supported file types


class WhisperSettings(BaseModel):
    """Settings for Whisper audio transcription."""
    model_size: str = "large-v2"
    device: str = "cuda"  # or "cpu"
    compute_type: str = "float16"


class ScraperSettings(BaseModel):
    """Settings for web scraping."""
    timeout: int = 30
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 DocuMind/1.0"
    max_content_length: int = 10 * 1024 * 1024  # 10MB


class FileSettings(BaseModel):
    allowed_types: str = "pdf,docx,xlsx,xls,csv,pptx,png,jpg,jpeg,bmp,tiff,webp"
    max_size: int = 100 * 1024 * 1024  # 100MB
    max_text_length: int = 50

    @property
    def allowed_types_list(self) -> List[str]:
        return [ext.strip() for ext in self.allowed_types.split(",")]


class WorkerSettings(BaseModel):
    concurrency: int = 1
    track_started: bool = True
    serializer: str = "json"
    soft_time_limit: int = 3600
    time_limit: int = 3660
    acks_late: bool = True
    reject_on_worker_lost: bool = True
    backend_callback_url: str = ""


class Settings(BaseSettings):
    """
    Main application settings.
    To override nested settings via env vars, use double underscores:
    e.g. MONGO__URL=...
    """
    app_name: str = "DocuMind"
    app_version: str = "1.0.0"
    
    # Nested configurations
    mongo: MongoSettings = MongoSettings()
    redis: RedisSettings = RedisSettings()
    llm: LLMSettings = LLMSettings()
    vlm: VLMSettings = VLMSettings()
    ocr: OCRSettings = OCRSettings()
    chroma: ChromaSettings = ChromaSettings()
    llama_cloud: LlamaCloudSettings = LlamaCloudSettings()
    whisper: WhisperSettings = WhisperSettings()
    scraper: ScraperSettings = ScraperSettings()
    file: FileSettings = FileSettings()
    worker: WorkerSettings = WorkerSettings()

    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: str = "logs/extractor.log"
    
    # Support for legacy flat env vars (optional, but good for backward compat if needed)
    # For this refactor, we are mapping them manually if Pydantic's aliases aren't used.
    # Pydantic v2 model_config allows env_nested_delimiter

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
