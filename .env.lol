# Environment Configuration Template
# Copy this file to .env and update with your values

# Application
APP_NAME=DocuMind
APP_VERSION=1.0.0

# MongoDB Configuration
MONGO_URL=mongodb://localhost:27017/
MONGO_DB=DocuMind
MONGO_COLLECTION=extractions

# LLM Configuration (Ollama)
LLM__MODEL=qwen3:14b
LLM__TEMPERATURE=0.2
LLM__BASE_URL=http://192.168.100.10:11434

# Embedding Configuration
LLM__EMBEDDING_MODEL=nomic-embed-text

# VLM Configuration (Groq Vision Model)
VLM__PROVIDER=groq
VLM__MODEL=meta-llama/llama-4-scout-17b-16e-instruct
VLM__API_KEY=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
VLM__API_URL=https://api.groq.com/openai/v1/chat/completions
VLM__TIMEOUT=120


# OCR Configuration
OCR_ENABLED=true
OCR_LANGUAGES=en,ar
OCR_GPU=false

# ChromaDB Configuration
CHROMA_DB_DIR=assets/memories/chroma_db

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6380
REDIS_DB=0
# REDIS_USERNAME=
# REDIS_PASSWORD=
REDIS_SSL=false

# File Processing
FILE_MAX_SIZE=104857600
MAX_TEXT_LENGTH=50

# LlamaCloud Configuration
LLAMA_CLOUD_API_KEY=llx-VOxhnV3693jdA1LGBfu6GkdR1x6ENSAIh13NlqC0P7nM0Bza
LLAMA_CLOUD_TIER_PARSING=free
TIMEOUT_PARSE_DOCUMENT=300

# Worker Configuration
WORKER__BACKEND_CALLBACK_URL=https://webhook.site/e0d97e11-776e-4ceb-a382-fe61e6558bea
