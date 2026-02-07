# DocuMind API Reference

Complete API documentation for DocuMind's REST endpoints.

## Base URL

```
http://localhost:8000
```

## Authentication

> **Note**: Authentication is not enabled by default. For production deployments, implement JWT or API key authentication.

---

## Endpoints

### Health Check

#### `GET /`

Check if the API is running.

**Response:**
```json
{
  "status": "healthy",
  "app": "DocuMind",
  "version": "1.0.0"
}
```

---

### Document Extraction

#### `POST /api/v1/extract`

Upload a file or URL for processing.

**Request (File Upload):**
```bash
curl -X POST "http://localhost:8000/api/v1/extract" \
  -F "file=@document.pdf" \
  -F "author=John Doe" \
  -F "description=Quarterly Report"
```

**Request (URL):**
```bash
curl -X POST "http://localhost:8000/api/v1/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/article",
    "author": "Jane Doe",
    "description": "Blog article"
  }'
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File | No* | Document file to process |
| `url` | string | No* | URL to scrape (website or YouTube) |
| `author` | string | No | Document author |
| `description` | string | No | Document description |
| `session_id` | string | No | Session ID for grouping documents |

*Either `file` or `url` is required.

**Supported File Types:**
- Documents: `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.xls`, `.csv`, `.txt`
- Images: `.png`, `.jpg`, `.jpeg`, `.tiff`, `.webp`
- Media: `.mp4`, `.mp3`, `.wav`, `.m4a`

**Response:**
```json
{
  "task_id": "abc123-def456",
  "status": "processing",
  "message": "Document queued for processing"
}
```

---

### Chat / Query

#### `POST /api/v1/chat`

Query your indexed documents.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key findings in the report?",
    "session_id": "user-session-123"
  }'
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Question to ask |
| `session_id` | string | Yes | Session ID to query against |
| `k` | integer | No | Number of context chunks (default: 5) |

**Response:**
```json
{
  "answer": "The key findings include...",
  "sources": [
    {
      "document": "quarterly_report.pdf",
      "page": 3,
      "relevance": 0.92
    }
  ],
  "cached": false
}
```

---

#### `POST /api/v1/chat/stream`

Stream chat responses via Server-Sent Events.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Summarize the document",
    "session_id": "user-session-123"
  }'
```

**Response (SSE):**
```
data: {"token": "The"}
data: {"token": " document"}
data: {"token": " discusses"}
...
data: {"done": true}
```

---

### Documents

#### `GET /api/v1/documents`

List all processed documents.

**Request:**
```bash
curl "http://localhost:8000/api/v1/documents?session_id=user-session-123"
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | No | Filter by session |
| `limit` | integer | No | Max results (default: 50) |
| `offset` | integer | No | Pagination offset |

**Response:**
```json
{
  "documents": [
    {
      "id": "doc-123",
      "filename": "report.pdf",
      "status": "completed",
      "created_at": "2024-01-15T10:30:00Z",
      "pages": 25
    }
  ],
  "total": 1
}
```

---

#### `DELETE /api/v1/documents/{document_id}`

Delete a processed document.

**Request:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/documents/doc-123"
```

**Response:**
```json
{
  "message": "Document deleted successfully"
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message here",
  "code": "ERROR_CODE"
}
```

**Common Error Codes:**
| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_FILE_TYPE` | 400 | Unsupported file format |
| `FILE_TOO_LARGE` | 413 | File exceeds size limit |
| `DOCUMENT_NOT_FOUND` | 404 | Document ID not found |
| `PROCESSING_ERROR` | 500 | Internal processing failure |

---

## Rate Limits

Default rate limits (configurable):
- 100 requests/minute per IP
- 10 concurrent file uploads

---

## Interactive Documentation

When the server is running, access interactive docs at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
