# RAG Enterprise System

A Retrieval-Augmented Generation (RAG) enterprise system designed for document ingestion, embedding generation, and semantic search capabilities. Built with FastAPI, PostgreSQL with pgvector, and MinIO for object storage.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   FastAPI App   │────▶│   PostgreSQL    │     │     MinIO       │
│   (Port 8000)   │     │   + pgvector    │     │  Object Storage │
│                 │────▶│   (Port 5432)   │     │  (Port 9000/01) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Components

- **FastAPI**: REST API server for document management and RAG queries
- **PostgreSQL + pgvector**: Vector database for storing document embeddings and similarity searches
- **MinIO**: S3-compatible object storage for raw document files
- **Anthropic Claude**: AI model for generating embeddings and completions

## Prerequisites

- Docker and Docker Compose
- Anthropic API Key (get one at https://console.anthropic.com/)

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd rag-enterprise-system
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

4. **Access the services**
   - API Documentation: http://localhost:8000/docs
   - MinIO Console: http://localhost:9001 (minioadmin/minioadmin123)

## Development

### Running Services

```bash
# Start all services
docker-compose up -d

# Start only infrastructure (PostgreSQL + MinIO)
docker-compose up -d postgres minio

# View logs
docker-compose logs -f api

# Rebuild API after changes
docker-compose build api && docker-compose up -d api

# Stop all services
docker-compose down
```

### Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run API with hot-reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Access

```bash
# Connect to PostgreSQL
docker exec -it rag-postgres psql -U rag_user -d rag_db

# Verify pgvector extension
docker exec -it rag-postgres psql -U rag_user -d rag_db -c \
  "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

## API Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| GET | `/` | API info | Implemented |
| GET | `/health` | Health check | Implemented |
| POST | `/api/v1/upload` | Upload a document | Implemented |
| GET | `/api/v1/documents/{id}` | Get document status | Implemented |
| GET | `/api/v1/documents/{id}/chunks` | Get document chunks | Implemented |
| GET | `/api/v1/documents` | List all documents | Planned |
| DELETE | `/api/v1/documents/{id}` | Delete a document | Planned |
| POST | `/api/v1/query` | Perform semantic search | Planned |

### Upload Endpoint

Upload documents for processing. Accepts PDF, DOCX, TXT, and Markdown files up to 50MB.

```bash
# Upload a PDF
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "file=@document.pdf"

# Response (201 Created)
{
  "doc_id": 1,
  "filename": "document.pdf",
  "status": "pending",
  "minio_object_key": "documents/2024/01/1_document.pdf"
}
```

**Error Responses:**
| Code | Description |
|------|-------------|
| 400 | Invalid file type (only PDF, DOCX, TXT, MD) |
| 413 | File too large (max 50MB) |
| 422 | No file provided |
| 503 | Storage service unavailable |

### Document Status Endpoint

Get the processing status of an uploaded document.

```bash
curl "http://localhost:8000/api/v1/documents/1"

# Response (200 OK)
{
  "id": 1,
  "filename": "document.pdf",
  "status": "completed",
  "page_count": 5,
  "text_preview": "First 200 characters of extracted text...",
  "error": null,
  "processed_at": "2024-01-15T10:30:00Z",
  "upload_timestamp": "2024-01-15T10:29:00Z"
}
```

**Status Values:** `pending` → `processing` → `completed` | `extraction_failed` | `error`

### Document Chunks Endpoint

Get all text chunks for a processed document.

```bash
curl "http://localhost:8000/api/v1/documents/1/chunks"

# Response (200 OK)
{
  "document_id": 1,
  "filename": "document.pdf",
  "status": "completed",
  "total_chunks": 3,
  "chunks": [
    {
      "id": 1,
      "chunk_index": 0,
      "content": "Text content of chunk...",
      "metadata": {"start_char": 0, "end_char": 1000, "filename": "document.pdf"},
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

Full API documentation available at http://localhost:8000/docs

## Database Schema

### Documents Table
Stores document metadata and processing status.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| filename | VARCHAR(255) | Original filename |
| content_type | VARCHAR(100) | MIME type |
| file_size | INTEGER | Size in bytes |
| minio_object_key | VARCHAR(500) | MinIO storage reference |
| processing_status | VARCHAR(50) | pending/processing/completed/extraction_failed/error |
| page_count | INTEGER | Number of pages (for PDFs) |
| extraction_error | TEXT | Error message if extraction failed |
| processed_at | TIMESTAMP | When processing completed |
| upload_timestamp | TIMESTAMP | When document was uploaded |
| metadata | JSONB | Additional attributes |

### Document Chunks Table
Stores text chunks with vector embeddings.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key (auto-increment) |
| document_id | INTEGER | Foreign key to documents (CASCADE delete) |
| chunk_index | INTEGER | Position in document (0-indexed) |
| content | TEXT | Chunk text content |
| embedding | VECTOR(1024) | Vector embedding (null until generated) |
| metadata | JSONB | Position info (start_char, end_char, filename) |
| created_at | TIMESTAMP | When chunk was created |

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | (set in docker-compose) |
| MINIO_ENDPOINT | MinIO server endpoint | minio:9000 |
| MINIO_ACCESS_KEY | MinIO access key | minioadmin |
| MINIO_SECRET_KEY | MinIO secret key | minioadmin123 |
| MINIO_SECURE | Use HTTPS for MinIO | false |
| ANTHROPIC_API_KEY | Claude API key | (required) |

### Vector Configuration

- **Dimensions**: 1024
- **Index Type**: IVFFlat with 100 lists
- **Distance Metric**: Cosine similarity

## Error Handling

The system implements a comprehensive exception hierarchy with custom handlers for production-ready error responses.

### Exception Categories

| Category | Exceptions | HTTP Status |
|----------|------------|-------------|
| Document | `DocumentNotFoundError`, `InvalidFileTypeError`, `FileSizeExceededError` | 404, 400, 413 |
| Storage | `StorageConnectionError`, `BucketNotFoundError`, `FileUploadError`, `FileDownloadError` | 503 |
| Preprocessing | `ExtractionError`, `CorruptedFileError`, `UnsupportedFormatError`, `ChunkingError` | 500, 422, 415, 500 |
| Processing | `DocumentProcessingError`, `StatusUpdateError` | 500 |

### Error Response Format

All errors return a consistent JSON structure:

```json
{
  "detail": "Human-readable error message",
  "error_code": "DOCUMENT_NOT_FOUND",
  "context": {"document_id": 123}
}
```

## Observability

### Structured Logging

The system uses `structlog` for JSON-formatted logging with contextual information:

- Request/response logging via middleware
- Processing pipeline events
- Error tracking with stack traces
- Document lifecycle events

### HTTP Logging Middleware

All HTTP requests are logged with:
- Request method and path
- Response status code
- Processing duration
- Client information

## Document Processing Pipeline

| Step | Description | Status |
|------|-------------|--------|
| 1. Upload | Store document in MinIO, create record with `status='pending'` | Implemented |
| 2. Background Processing | Download from MinIO, extract text (PDF, DOCX, TXT, MD) | Implemented |
| 3. Chunking | Split text into overlapping chunks (1000 chars, 200 overlap) | Implemented |
| 4. Storage | Store chunks in `document_chunks` with position metadata | Implemented |
| 5. Completion | Update document `status` to `'completed'` | Implemented |
| 6. Embedding Generation | Generate embeddings via Claude API | Planned |
| 7. Semantic Search | Query similar chunks using pgvector | Planned |

### Chunking Configuration
- **Chunk Size**: 1000 characters
- **Overlap**: 200 characters
- **Separator**: Paragraph boundaries (`\n\n`)
- Chunks preserve word boundaries

## Project Structure

```
rag-enterprise-system/
├── src/                          # Application source code
│   ├── api/
│   │   ├── routes.py             # API route definitions
│   │   └── exception_handlers.py # Custom exception handlers
│   ├── config/
│   │   ├── settings.py           # Environment configuration
│   │   └── database.py           # SQLAlchemy session management
│   ├── exceptions/               # Custom exception hierarchy
│   │   ├── base.py               # RAGSystemError base class
│   │   ├── document.py           # Document-related exceptions
│   │   ├── preprocessing.py      # Extraction/chunking exceptions
│   │   ├── processing.py         # Processing pipeline exceptions
│   │   └── storage.py            # Storage/MinIO exceptions
│   ├── middleware/
│   │   └── logging_middleware.py # HTTP request/response logging
│   ├── models/
│   │   ├── database.py           # ORM models (Document, DocumentChunk)
│   │   └── schemas.py            # Pydantic request/response schemas
│   ├── preprocessing/
│   │   ├── extractors.py         # Text extraction (PDF, DOCX, TXT, MD)
│   │   └── chunking.py           # Semantic text chunking with overlap
│   ├── services/
│   │   ├── storage_service.py    # MinIO client wrapper
│   │   ├── document_service.py   # Document upload logic
│   │   ├── background_tasks.py   # Async processing (extraction + chunking)
│   │   └── embedding_service.py  # Embedding generation (stub)
│   ├── utils/
│   │   └── logging.py            # Structured JSON logging utilities
│   └── main.py                   # Application entry point
├── tests/                        # Test files (145 tests)
│   ├── conftest.py               # Pytest fixtures
│   ├── test_storage_service.py   # Storage unit tests
│   ├── test_document_service.py  # Document unit tests
│   ├── test_upload_endpoint.py   # API integration tests
│   ├── test_background_tasks.py  # Background task tests
│   ├── test_extractors.py        # Extractor unit tests
│   ├── test_chunking.py          # Chunking unit tests
│   ├── test_exception_handlers.py # Exception handler tests
│   └── test_exceptions.py        # Exception tests
├── init-db/                      # Database initialization scripts
│   └── 01-init.sql               # Schema and pgvector setup
├── migrations/                   # Database migrations
│   └── 003_add_extraction_columns.sql
├── scripts/                      # Utility scripts
├── docker-compose.yml            # Container orchestration
├── docker-compose.debug.yml      # Debug configuration
├── Dockerfile                    # API container build
├── requirements.txt              # Python dependencies
└── CLAUDE.md                     # AI assistant instructions
```

## Testing

```bash
# Activate virtual environment
source .venv/bin/activate

# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=term-missing
```

## License

[Add your license here]