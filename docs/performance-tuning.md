# DocuMind Performance Tuning Guide

Optimize DocuMind for maximum throughput and efficiency.

## Quick Wins

### 1. Enable Semantic Caching

Semantic caching dramatically reduces response times for similar queries:

```env
# .env
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_TTL=3600  # 1 hour
SEMANTIC_CACHE_THRESHOLD=0.85  # Similarity threshold
```

**Impact**: 50-90% reduction in response time for cached queries.

### 2. Optimize Chunk Size

Adjust chunk size based on your document types:

```python
# For technical documents (code, specs)
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# For narrative content (reports, articles)
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
```

### 3. Increase Celery Workers

Scale workers based on CPU cores:

```bash
# Production recommendation: 2-4 workers per CPU core
celery -A worker.celery_app worker \
  --concurrency=8 \
  --loglevel=info \
  -Q extraction_queue
```

---

## OCR Optimization

### PaddleOCR Settings

```python
# Optimize for speed
ocr = PaddleOCR(
    use_angle_cls=False,  # Disable if documents are upright
    lang='en',
    use_gpu=True,  # If CUDA available
    det_limit_side_len=960,  # Reduce for faster detection
)
```

### VLM Fallback Threshold

Adjust the confidence threshold to balance accuracy vs. speed:

```env
# Lower = more VLM calls (slower, more accurate)
# Higher = fewer VLM calls (faster, may miss complex content)
OCR_CONFIDENCE_THRESHOLD=0.7
```

---

## Database Optimization

### MongoDB Indexes

Create indexes for common queries:

```javascript
// In MongoDB shell
db.documents.createIndex({ "session_id": 1 });
db.documents.createIndex({ "created_at": -1 });
db.documents.createIndex({ "status": 1, "session_id": 1 });
```

### ChromaDB Settings

```python
# Use persistent storage for production
chroma_client = chromadb.PersistentClient(
    path="/data/chromadb",
    settings=Settings(
        anonymized_telemetry=False,
        allow_reset=False
    )
)
```

### Connection Pooling

```python
# MongoDB connection pooling
client = MongoClient(
    MONGO_URL,
    maxPoolSize=50,
    minPoolSize=10,
    maxIdleTimeMS=30000
)
```

---

## API Performance

### Enable Response Compression

```python
from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### Async Everywhere

Ensure all I/O operations are async:

```python
# Good - async database call
async def get_document(doc_id: str):
    return await db.documents.find_one({"_id": doc_id})

# Bad - blocking call
def get_document(doc_id: str):
    return db.documents.find_one({"_id": doc_id})
```

### Request Timeouts

```python
# Set appropriate timeouts
import httpx

async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.post(url, data=data)
```

---

## Memory Optimization

### Streaming Large Files

Process large files in chunks to avoid memory issues:

```python
async def process_large_pdf(file_path: str):
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            yield text  # Process page by page
```

### Garbage Collection

For long-running workers:

```python
import gc

def process_document(doc):
    result = heavy_processing(doc)
    gc.collect()  # Force garbage collection
    return result
```

---

## Benchmarks

### Expected Performance

| Operation | Time (avg) | Optimized |
|-----------|------------|-----------|
| PDF extraction (10 pages) | 5s | 2s |
| Image OCR | 3s | 1.5s |
| Chat query (cached) | 50ms | 20ms |
| Chat query (uncached) | 2s | 1s |
| Document indexing | 1s | 0.5s |

### Running Benchmarks

```bash
# Install benchmark tools
pip install pytest-benchmark

# Run performance tests
pytest tests/benchmarks/ --benchmark-only
```

---

## Monitoring Metrics

Track these key metrics:

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| API latency (p95) | <500ms | >1000ms |
| Cache hit rate | >70% | <50% |
| Worker queue depth | <100 | >500 |
| Memory usage | <80% | >90% |

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram

REQUEST_LATENCY = Histogram(
    'request_latency_seconds',
    'Request latency',
    ['endpoint']
)

CACHE_HITS = Counter(
    'cache_hits_total',
    'Number of cache hits'
)
```

---

## Troubleshooting

### Slow Document Processing

1. Check worker logs for bottlenecks
2. Profile extraction code
3. Consider GPU acceleration for OCR

### High Memory Usage

1. Reduce worker concurrency
2. Implement file size limits
3. Process large files in streaming mode

### Redis Connection Issues

1. Check connection pool settings
2. Verify network connectivity
3. Consider Redis Cluster for high load
