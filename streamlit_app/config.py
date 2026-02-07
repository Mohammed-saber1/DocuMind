"""
DocuMind Streamlit Configuration 🧠
====================================

Central configuration for the Streamlit frontend.
"""

# Backend API Settings
API_BASE_URL = "http://localhost:8005/api/v1"
EXTRACTION_ENDPOINT = f"{API_BASE_URL}/extract/"
CHAT_ENDPOINT = f"{API_BASE_URL}/chat/"
CHAT_STREAM_ENDPOINT = f"{API_BASE_URL}/chat/stream"

# Hidden Defaults (not exposed in UI)
DEFAULT_OCR_VLM = True
DEFAULT_K = 8

# Supported File Types
SUPPORTED_FILES = {
    "pdf": {"icon": "📄", "label": "PDF", "extensions": ["pdf"]},
    "ppt": {"icon": "📊", "label": "PowerPoint", "extensions": ["ppt", "pptx"]},
    "word": {"icon": "📝", "label": "Word", "extensions": ["doc", "docx"]},
    "txt": {"icon": "📃", "label": "Text", "extensions": ["txt"]},
    "image": {"icon": "🖼️", "label": "Image", "extensions": ["png", "jpg", "jpeg", "gif", "webp"]},
    "audio": {"icon": "🎧", "label": "Audio", "extensions": ["mp3", "wav", "m4a", "ogg"]},
    "video": {"icon": "🎬", "label": "Video", "extensions": ["mp4", "avi", "mov", "mkv", "webm"]},
}

# URL Types
URL_TYPES = {
    "website": {"icon": "🌐", "label": "Website URL", "placeholder": "https://example.com"},
    "youtube": {"icon": "▶️", "label": "YouTube URL", "placeholder": "https://youtube.com/watch?v=..."},
}

# All supported extensions for file uploader
ALL_EXTENSIONS = []
for file_type in SUPPORTED_FILES.values():
    ALL_EXTENSIONS.extend(file_type["extensions"])

# App Metadata
APP_TITLE = "DocuMind 🧠"
APP_TAGLINE = "Turn unstructured data into intelligence"
