from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Response model for document upload endpoint."""
    doc_id: int
    filename: str
    status: str
