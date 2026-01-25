"""Response enumerations for API responses."""
from enum import Enum


class ResponseStatusEnum(str, Enum):
    """API response status codes."""
    SUCCESS = "success"
    ERROR = "error"
    PROCESSING = "processing"
    PENDING = "pending"


class ExtractionStatusEnum(str, Enum):
    """Document extraction status."""
    QUEUED = "queued"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"
