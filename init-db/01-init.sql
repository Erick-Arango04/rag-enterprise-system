-- Habilitar la extensión pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabla de documentos
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100),
    file_size INTEGER,
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_status VARCHAR(50) DEFAULT 'pending',
    metadata JSONB,
    minio_object_key VARCHAR(500)
);

-- Tabla de chunks con vectores
CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1024),  -- Claude embeddings son 1024 dimensiones
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice para búsqueda vectorial (usaremos HNSW para producción)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
ON document_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Índice para búsquedas por documento
CREATE INDEX IF NOT EXISTS idx_chunks_document_id
ON document_chunks(document_id);

-- Verificar que pgvector está instalado
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';