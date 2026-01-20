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

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/documents` | Upload a document |
| GET | `/documents` | List all documents |
| GET | `/documents/{id}` | Get document details |
| DELETE | `/documents/{id}` | Delete a document |
| POST | `/query` | Perform semantic search |

Full API documentation available at http://localhost:8000/docs

## Database Schema

### Documents Table
Stores document metadata and processing status.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| filename | VARCHAR | Original filename |
| content_type | VARCHAR | MIME type |
| file_size | BIGINT | Size in bytes |
| minio_object_key | VARCHAR | MinIO storage reference |
| processing_status | VARCHAR | pending/processing/completed/failed |
| metadata | JSONB | Additional attributes |

### Document Chunks Table
Stores text chunks with vector embeddings.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| document_id | UUID | Foreign key to documents |
| chunk_index | INTEGER | Position in document |
| content | TEXT | Chunk text content |
| embedding | VECTOR(1024) | Vector embedding |
| metadata | JSONB | Additional attributes |

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

## Document Processing Pipeline

1. Upload document to MinIO object storage
2. Create document record with `processing_status='pending'`
3. Extract and chunk document text
4. Generate embeddings for each chunk via Claude API
5. Store chunks with embeddings in pgvector
6. Update document status to `'completed'`

## Project Structure

```
rag-enterprise-system/
├── src/                    # Application source code
├── init-db/                # Database initialization scripts
│   └── 01-init.sql         # Schema and pgvector setup
├── docs/                   # Documentation
├── tests/                  # Test files
├── docker-compose.yml      # Container orchestration
├── Dockerfile              # API container build
├── requirements.txt        # Python dependencies
└── CLAUDE.md               # AI assistant instructions
```

## License

[Add your license here]