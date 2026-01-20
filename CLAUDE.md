# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a RAG (Retrieval-Augmented Generation) enterprise system designed for document ingestion, embedding generation, and semantic search capabilities. The system uses PostgreSQL with the pgvector extension for vector similarity search.

## Architecture

### Application Layer
- **FastAPI**: REST API server for document management and RAG queries
- **Python 3.11** with Uvicorn ASGI server
- **Dependencies**:
  - SQLAlchemy for database ORM
  - Anthropic SDK for Claude API integration (embeddings/completions)
  - Document processing libraries (pypdf, python-docx, openpyxl)
  - MinIO SDK for object storage
  - Pydantic for data validation

### Database Layer
- **PostgreSQL with pgvector**: Vector database for storing document embeddings and performing similarity searches
- **Schema**:
  - `documents`: Stores document metadata including filename, content type, file size, processing status, and MinIO object keys
  - `document_chunks`: Stores text chunks with their vector embeddings (1024 dimensions) and associated metadata
  - Vector search uses IVFFlat indexing with cosine similarity (`vector_cosine_ops`)

### Object Storage Layer
- **MinIO**: S3-compatible object storage for storing raw document files
- Provides both API (port 9000) and Web Console UI (port 9001)
- Documents are referenced in PostgreSQL via `minio_object_key` field

### Storage Strategy
- Documents are stored in MinIO (object storage), referenced by `minio_object_key` in the documents table
- Documents are chunked for embedding generation, with each chunk stored separately in `document_chunks`
- Chunks maintain references to their parent document via `document_id` foreign key
- All services run on the same Docker network (`rag-network`) for inter-service communication

### Directory Structure
- `src/`: Source code (currently empty - implementation pending)
- `init-db/`: PostgreSQL initialization scripts
  - `01-init.sql`: Creates pgvector extension, tables, and indexes
- `docs/`: Documentation (currently empty)
- `data/`: Local data storage (gitignored)
- `tests/`: Test files (currently empty)

## Development Commands

### Infrastructure Setup

**First-time setup:**
```bash
# 1. Configure your .env file with a valid ANTHROPIC_API_KEY
# Get your API key from https://console.anthropic.com/
# Edit .env and replace 'your_actual_api_key_here' with your real key

# 2. Start all services
docker-compose up -d
```

**Common commands:**
```bash
# Start all services (PostgreSQL + MinIO + API)
docker-compose up -d

# Start only infrastructure services (without API)
docker-compose up -d postgres minio

# Build and start the API service
docker-compose build api
docker-compose up -d api

# Restart a service after config changes
docker-compose restart api

# Check service health
docker-compose ps

# View logs for specific service
docker-compose logs -f postgres
docker-compose logs -f minio
docker-compose logs -f api

# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: destroys all data)
docker-compose down -v
```

### API Development
```bash
# Run API locally (outside Docker) - requires virtual environment
source .venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Install dependencies locally
pip install -r requirements.txt

# API will be available at http://localhost:8000
# Interactive API docs at http://localhost:8000/docs
```

### API Connection
- **Base URL**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative docs**: http://localhost:8000/redoc (ReDoc)

### Database Connection
- **Host**: localhost
- **Port**: 5432
- **Database**: rag_db
- **User**: rag_user
- **Password**: rag_password

### Database Access
```bash
# Connect to PostgreSQL directly
docker exec -it rag-postgres psql -U rag_user -d rag_db

# Verify pgvector installation
docker exec -it rag-postgres psql -U rag_user -d rag_db -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

### MinIO Connection
- **API Endpoint**: http://localhost:9000
- **Console UI**: http://localhost:9001
- **Root User**: minioadmin
- **Root Password**: minioadmin123

### MinIO Access
```bash
# Access MinIO Web Console
# Navigate to http://localhost:9001 in your browser
# Login with minioadmin/minioadmin123

# Using MinIO Client (mc) - if installed
mc alias set local http://localhost:9000 minioadmin minioadmin123
mc ls local
mc mb local/documents  # Create a bucket for documents
```

## Key Technical Details

### Embedding Configuration
- Vector dimensions: **1024** (configured in `document_chunks.embedding` column)
- When implementing embedding generation, ensure the model outputs 1024-dimensional vectors

### Vector Indexing
- Index type: **IVFFlat** with 100 lists
- Distance metric: **Cosine similarity** (`vector_cosine_ops`)
- For production workloads with large datasets, consider adjusting the `lists` parameter based on dataset size

### Document Processing Pipeline
The expected workflow (based on schema design):
1. Upload document → store in MinIO
2. Create entry in `documents` table with `processing_status='pending'`
3. Process document into chunks
4. Generate embeddings for each chunk
5. Store chunks with embeddings in `document_chunks`
6. Update document `processing_status` to 'completed'

## Implementation Notes

### Environment Variables
The API service requires the following environment variables (automatically configured in docker-compose.yml):
- `DATABASE_URL`: PostgreSQL connection string
- `MINIO_ENDPOINT`: MinIO server endpoint
- `MINIO_ACCESS_KEY`: MinIO access credentials
- `MINIO_SECRET_KEY`: MinIO secret credentials
- `MINIO_SECURE`: Whether to use HTTPS for MinIO (false in development)
- `ANTHROPIC_API_KEY`: Required for Claude API calls (must be set manually)

### Development Notes
- The project uses Python 3.11 with FastAPI framework
- Source code directory (`src/`) is currently being implemented
- JSONB metadata fields in both tables allow flexible storage of additional attributes without schema changes
- Cascade delete on `document_chunks` ensures cleanup when documents are removed
- Hot-reload is enabled in Docker via volume mount (`./src:/app/src`)
- The Anthropic SDK is used for generating embeddings via Claude API