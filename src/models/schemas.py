from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UploadResponse(BaseModel):
    """Response model for document upload endpoint."""

    doc_id: int
    filename: str
    status: str
    minio_object_key: str
    message: str = "Processing started"


class DocumentStatusResponse(BaseModel):
    """Response model for document status endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    status: str
    page_count: Optional[int] = None
    text_preview: Optional[str] = None
    error: Optional[str] = None
    processed_at: Optional[datetime] = None
    upload_timestamp: Optional[datetime] = None


class ChunkResponse(BaseModel):
    """Response model for a single document chunk."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    chunk_index: int
    content: str
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None


class DocumentChunksResponse(BaseModel):
    """Response model for document chunks endpoint."""

    document_id: int
    filename: str
    status: str
    total_chunks: int
    chunks: list[ChunkResponse]
