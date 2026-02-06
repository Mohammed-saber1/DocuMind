# DocuMind 🧠

**Intelligent Document Extraction & Intelligence Platform**

DocuMind is a powerful, production-ready document processing pipeline designed to transform unstructured data (files, URLs, videos) into structured, actionable intelligence. It combines state-of-the-art OCR, Vision-Language Models (VLM), and Large Language Models (LLM) to extract, analyze, and index information for Retrieval-Augmented Generation (RAG) workflows.

---

## 🚀 Key Features

*   **Universal Input Support**: Process a wide range of formats including:
    *   **Documents**: PDF, DOCX, PPTX, XLSX, CSV, TXT.
    *   **Images**: PNG, JPG, TIFF, WEBP (with automatic OCR).
    *   **Multimedia**: Audio and Video files (MP4, MP3, WAV) via OpenAI Whisper.
    *   **Web**: Scrape websites and process YouTube videos (transcription + meta-data).
*   **Smart Vision Pipeline**:
    *   **Hybrid OCR/VLM**: Automatically detects if OCR is sufficient. If confidence is low or images are complex, it seamlessly falls back to Vision-Language Models (e.g., Mistral/Groq) for deep visual understanding.
*   **High-Performance RAG**:
    *   **Semantic Caching**: Redis-based caching layer for instant responses to similar queries (exact & semantic match).
    *   **Streaming Responses**: Interactive chat experience with Server-Sent Events (SSE).
    *   **Optimized Indexing**: Automatically chunks and indexes extracted text into **ChromaDB**.
*   **Structured Data Extraction**: Uses LLM Agents to parse raw text into clean, structured JSON schemas.
*   **Scalable Architecture**: Built on **FastAPI** and **Celery** for asynchronous, distributed processing.

---

## 🛠️ Technology Stack

*   **Framework**: FastAPI (Python)
*   **Asynchronous Tasks**: Celery + Redis
*   **Database**: MongoDB (Metadata), ChromaDB (Vector Store)
*   **LLM & Orchestration**: LangChain, Ollama
*   **OCR**: PaddleOCR / Tesseract
*   **Audio**: OpenAI Whisper
*   **Deployment**: Docker & Docker Compose

---

## 🏗️ Architecture Overview

The system follows a modular **Controller-Service-Repository** pattern:

1.  **Ingestion**: Files or URLs are submitted via the API.
2.  **Extraction**: Specialized extractors handle specific formats (e.g., `pdf_extractor`, `youtube_extractor`).
3.  **Analysis**:
    *   Images pass through the **OCR Service**. Complex images are routed to the **VLM Service**.
    *   Audio/Video is transcribed.
4.  **Transformation**: The **Agent** structures the raw data.
5.  **Indexing**: Data is saved to **MongoDB** and vector-indexed in **ChromaDB**.
6.  **Retrieval**: The **Chat Service** uses the vector store and **Redis Semantic Cache** to answer user queries efficiently.

---

## 📂 Project Structure

```bash
DocuMind/
├── docker/             # Docker configuration files
├── src/
│   ├── config/         # Application settings
│   ├── controllers/    # API Request Handlers
│   ├── core/           # Core configuration & startup logic
│   ├── extractors/     # Format-specific logic (PDF, Word, URL, etc.)
│   ├── models/         # Pydantic models & DB Schemas
│   ├── pipeline/       # Main processing workflow
│   ├── routes/         # API Endpoints
│   ├── services/       # Business logic (Chat, OCR, DB, Memory, Cache)
│   ├── worker/         # Celery worker definitions
│   └── main.py         # App Entry point
├── .env.example        # Environment variable template
├── docker-compose.yml  # Container orchestration
└── requirements.txt    # Python dependencies
```

---

## 🚀 Getting Started

### Prerequisites

*   **Python 3.10+**
*   **Docker & Docker Compose**
*   **Ollama** (running locally for LLM/Embeddings)
*   **MongoDB** (running locally or via Docker)
*   **Redis** (running locally or via Docker)

### 1. Clone the Repository

```bash
git clone https://github.com/your-repo/documind.git
cd documind
```

### 2. Configure Environment

Copy the example environment file and configure your keys:

```bash
cp src/.env.example src/.env
```

Edit `src/.env` to set your configuration, especially:
- `VLM__API_KEY` (if using Groq/Mistral)
- `LLAMA_CLOUD_API_KEY` (if using LlamaCloud parsing)
- `REDIS_*` settings

### 3. Start Dependencies (Docker)

Use Docker Compose to start MongoDB, Redis, and other infrastructure services:

```bash
docker-compose -f docker/docker-compose.yml up -d
```

### 4. Install Python Dependencies

It is recommended to use a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r src/requirements.txt
```

### 5. Run the Application

Start the FastAPI server:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Start the Celery Worker (for background processing):

```bash
cd src
celery -A worker.celery_app worker --loglevel=info -Q extraction_queue
```

---

## 🔧 Troubleshooting

### PaddleOCR & NumPy Compatibility
If you encounter `module compiled against ABI version...` errors with PaddleOCR:
- Ensure you are using a compatible NumPy version (< 2.0.0).
- Run: `pip install "numpy<2.0"`

### Redis Connection
If caching fails, verify Redis is running on port 6380 (default in docker-compose) or update `src/.env`.

---

## 🔌 API Documentation

Once the server is running, access the interactive API docs at:

*   **Swagger UI**: `http://localhost:8000/docs`
*   **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

*   `POST /api/v1/extract`: Upload a file or URL for processing.
*   `POST /api/v1/chat`: Chat with your indexed documents.
*   `POST /api/v1/chat/stream`: Stream chat responses (SSE).
*   `GET /api/v1/documents`: List processed documents.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*Powered by [Mohammed Saber](https://www.linkedin.com/in/mohamedsaber14/)* 🧠
