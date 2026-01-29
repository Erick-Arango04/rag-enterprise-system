from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, ForeignKey
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from src.config.database import Base


class Document(Base):
    """SQLAlchemy model matching existing documents table schema."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100))
    file_size = Column(Integer)
    upload_timestamp = Column(DateTime, server_default=func.now())
    processing_status = Column(String(50), default="pending")
    doc_metadata = Column("metadata", JSON)
    minio_object_key = Column(String(500))
    extracted_text = Column(Text)
    page_count = Column(Integer)
    extraction_error = Column(Text)
    processed_at = Column(DateTime)


class DocumentChunk(Base):
    """SQLAlchemy model for document_chunks table."""
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1024))  # pgvector - null until embedding generation
    chunk_metadata = Column("metadata", JSON)
    created_at = Column(DateTime, server_default=func.now())
