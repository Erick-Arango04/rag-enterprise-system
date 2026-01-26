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
