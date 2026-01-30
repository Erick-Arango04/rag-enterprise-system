import pytest
from fastapi.testclient import TestClient

from src.models.database import DocumentChunk


class TestUploadEndpoint:
    """Integration tests for POST /api/v1/upload endpoint."""

    # Success cases
    def test_upload_pdf_returns_201(self, client, sample_pdf):
        """POST /upload with PDF returns 201 and UploadResponse."""
        filename, content, content_type = sample_pdf
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )

        assert response.status_code == 201
        data = response.json()
        assert "doc_id" in data
        assert data["filename"] == filename

    def test_upload_response_schema(self, client, sample_pdf):
        """Response contains doc_id, filename, status, minio_object_key."""
        filename, content, content_type = sample_pdf
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )

        data = response.json()
        assert "doc_id" in data
        assert "filename" in data
        assert "status" in data
        assert "minio_object_key" in data
        assert isinstance(data["doc_id"], int)
        assert isinstance(data["filename"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["minio_object_key"], str)

    def test_upload_response_minio_object_key_format(self, client, sample_pdf):
        """Upload response minio_object_key follows expected path format."""
        import re
        filename, content, content_type = sample_pdf
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )

        data = response.json()
        object_key = data["minio_object_key"]
        # Format: documents/{year}/{month}/{doc_id}_{filename}
        pattern = r"^documents/\d{4}/\d{2}/\d+_test\.pdf$"
        assert re.match(pattern, object_key), f"Object key '{object_key}' doesn't match expected format"

    def test_upload_status_is_pending(self, client, sample_pdf):
        """Uploaded document has status='pending'."""
        filename, content, content_type = sample_pdf
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )

        assert response.json()["status"] == "pending"

    def test_upload_txt_returns_201(self, client, sample_txt):
        """POST /upload with TXT returns 201."""
        filename, content, content_type = sample_txt
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )

        assert response.status_code == 201

    def test_upload_docx_returns_201(self, client, sample_docx):
        """POST /upload with DOCX returns 201."""
        filename, content, content_type = sample_docx
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )

        assert response.status_code == 201

    def test_upload_markdown_returns_201(self, client, sample_markdown):
        """POST /upload with Markdown returns 201."""
        filename, content, content_type = sample_markdown
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )

        assert response.status_code == 201

    # Error cases
    def test_upload_invalid_mime_returns_400(self, client, sample_invalid_file):
        """POST /upload with PNG returns 400."""
        filename, content, content_type = sample_invalid_file
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "InvalidFileTypeError"
        assert "message" in data
        assert data["details"]["content_type"] == "image/png"

    def test_upload_large_file_returns_413(self, client, sample_large_file):
        """POST /upload with >50MB file returns 413."""
        filename, content, content_type = sample_large_file
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )

        assert response.status_code == 413
        data = response.json()
        assert data["error_type"] == "FileSizeExceededError"
        assert "message" in data

    def test_upload_no_file_returns_422(self, client):
        """POST /upload without file returns 422."""
        response = client.post("/api/v1/upload")

        assert response.status_code == 422

    def test_upload_minio_down_returns_503(self, client_storage_unavailable, sample_pdf):
        """POST /upload when MinIO down returns 503."""
        filename, content, content_type = sample_pdf
        response = client_storage_unavailable.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )

        assert response.status_code == 503
        data = response.json()
        assert data["error_type"] == "StorageConnectionError"
        assert "message" in data

    # Response validation
    def test_error_response_has_correct_format(self, client, sample_invalid_file):
        """Error responses contain error_type and message fields."""
        filename, content, content_type = sample_invalid_file
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )

        data = response.json()
        assert "error_type" in data
        assert "message" in data


class TestDocumentStatusEndpoint:
    """Integration tests for GET /api/v1/documents/{document_id} endpoint."""

    def test_get_document_status_returns_200(self, client, sample_pdf):
        """GET /documents/{id} returns 200 for existing document."""
        # First upload a document
        filename, content, content_type = sample_pdf
        upload_response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )
        doc_id = upload_response.json()["doc_id"]

        # Then get its status
        response = client.get(f"/api/v1/documents/{doc_id}")

        assert response.status_code == 200

    def test_get_document_status_response_schema(self, client, sample_pdf):
        """Response contains expected fields."""
        filename, content, content_type = sample_pdf
        upload_response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )
        doc_id = upload_response.json()["doc_id"]

        response = client.get(f"/api/v1/documents/{doc_id}")
        data = response.json()

        assert "id" in data
        assert "filename" in data
        assert "status" in data
        assert "page_count" in data
        assert "text_preview" in data
        assert "error" in data
        assert "processed_at" in data
        assert "upload_timestamp" in data

    def test_get_document_status_returns_correct_data(self, client, sample_pdf):
        """Response contains correct document data."""
        filename, content, content_type = sample_pdf
        upload_response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )
        doc_id = upload_response.json()["doc_id"]

        response = client.get(f"/api/v1/documents/{doc_id}")
        data = response.json()

        assert data["id"] == doc_id
        assert data["filename"] == filename
        assert data["status"] == "pending"

    def test_get_document_not_found_returns_404(self, client):
        """GET /documents/{id} returns 404 for non-existent document."""
        response = client.get("/api/v1/documents/99999")

        assert response.status_code == 404
        data = response.json()
        assert data["error_type"] == "DocumentNotFoundError"
        assert data["details"]["document_id"] == 99999

    def test_get_document_invalid_id_returns_422(self, client):
        """GET /documents/{id} returns 422 for invalid document ID."""
        response = client.get("/api/v1/documents/0")

        assert response.status_code == 422

    def test_get_document_negative_id_returns_422(self, client):
        """GET /documents/{id} returns 422 for negative document ID."""
        response = client.get("/api/v1/documents/-1")

        assert response.status_code == 422


class TestDocumentChunksEndpoint:
    """Integration tests for GET /api/v1/documents/{document_id}/chunks endpoint."""

    def test_get_chunks_returns_200(self, client, db_session, sample_pdf):
        """GET /documents/{id}/chunks returns 200 for document with chunks."""
        # Upload document
        filename, content, content_type = sample_pdf
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )
        doc_id = response.json()["doc_id"]

        # Create a chunk
        chunk = DocumentChunk(
            document_id=doc_id,
            chunk_index=0,
            content="Test chunk content",
            chunk_metadata={"start_char": 0, "end_char": 18},
        )
        db_session.add(chunk)
        db_session.commit()

        # Test endpoint
        response = client.get(f"/api/v1/documents/{doc_id}/chunks")
        assert response.status_code == 200

    def test_get_chunks_response_schema(self, client, db_session, sample_pdf):
        """Response contains all required fields."""
        filename, content, content_type = sample_pdf
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )
        doc_id = response.json()["doc_id"]

        # Create a chunk
        chunk = DocumentChunk(
            document_id=doc_id,
            chunk_index=0,
            content="Test chunk content",
            chunk_metadata={"start_char": 0, "end_char": 18},
        )
        db_session.add(chunk)
        db_session.commit()

        response = client.get(f"/api/v1/documents/{doc_id}/chunks")
        data = response.json()

        # Verify top-level fields
        assert "document_id" in data
        assert "filename" in data
        assert "status" in data
        assert "total_chunks" in data
        assert "chunks" in data

        # Verify chunk fields
        assert len(data["chunks"]) == 1
        chunk_data = data["chunks"][0]
        assert "id" in chunk_data
        assert "chunk_index" in chunk_data
        assert "content" in chunk_data
        assert "metadata" in chunk_data
        assert "created_at" in chunk_data

    def test_get_chunks_returns_correct_document_info(self, client, db_session, sample_pdf):
        """Response contains correct document data."""
        filename, content, content_type = sample_pdf
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )
        doc_id = response.json()["doc_id"]

        response = client.get(f"/api/v1/documents/{doc_id}/chunks")
        data = response.json()

        assert data["document_id"] == doc_id
        assert data["filename"] == filename
        assert data["status"] == "pending"

    def test_get_chunks_returns_empty_list_for_document_without_chunks(self, client, sample_pdf):
        """Response returns empty chunks list when no chunks exist."""
        filename, content, content_type = sample_pdf
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )
        doc_id = response.json()["doc_id"]

        response = client.get(f"/api/v1/documents/{doc_id}/chunks")
        data = response.json()

        assert data["total_chunks"] == 0
        assert data["chunks"] == []

    def test_get_chunks_returns_chunks_ordered_by_index(self, client, db_session, sample_pdf):
        """Chunks are returned ordered by chunk_index."""
        filename, content, content_type = sample_pdf
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )
        doc_id = response.json()["doc_id"]

        # Create chunks out of order
        for idx in [2, 0, 1]:
            chunk = DocumentChunk(
                document_id=doc_id,
                chunk_index=idx,
                content=f"Chunk {idx} content",
                chunk_metadata={"index": idx},
            )
            db_session.add(chunk)
        db_session.commit()

        response = client.get(f"/api/v1/documents/{doc_id}/chunks")
        data = response.json()

        assert data["total_chunks"] == 3
        indices = [c["chunk_index"] for c in data["chunks"]]
        assert indices == [0, 1, 2]

    def test_get_chunks_returns_correct_chunk_content(self, client, db_session, sample_pdf):
        """Chunk content matches stored data."""
        filename, content, content_type = sample_pdf
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )
        doc_id = response.json()["doc_id"]

        expected_content = "This is specific chunk content for testing"
        chunk = DocumentChunk(
            document_id=doc_id,
            chunk_index=0,
            content=expected_content,
            chunk_metadata={},
        )
        db_session.add(chunk)
        db_session.commit()

        response = client.get(f"/api/v1/documents/{doc_id}/chunks")
        data = response.json()

        assert data["chunks"][0]["content"] == expected_content

    def test_get_chunks_returns_chunk_metadata(self, client, db_session, sample_pdf):
        """Chunk metadata is correctly returned."""
        filename, content, content_type = sample_pdf
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )
        doc_id = response.json()["doc_id"]

        expected_metadata = {"start_char": 0, "end_char": 100, "filename": "test.pdf"}
        chunk = DocumentChunk(
            document_id=doc_id,
            chunk_index=0,
            content="Test content",
            chunk_metadata=expected_metadata,
        )
        db_session.add(chunk)
        db_session.commit()

        response = client.get(f"/api/v1/documents/{doc_id}/chunks")
        data = response.json()

        assert data["chunks"][0]["metadata"] == expected_metadata

    def test_get_chunks_not_found_returns_404(self, client):
        """GET /documents/{id}/chunks returns 404 for non-existent document."""
        response = client.get("/api/v1/documents/99999/chunks")

        assert response.status_code == 404
        data = response.json()
        assert data["error_type"] == "DocumentNotFoundError"
        assert data["details"]["document_id"] == 99999

    def test_get_chunks_invalid_id_returns_422(self, client):
        """GET /documents/{id}/chunks returns 422 for invalid document ID."""
        response = client.get("/api/v1/documents/0/chunks")

        assert response.status_code == 422

    def test_get_chunks_negative_id_returns_422(self, client):
        """GET /documents/{id}/chunks returns 422 for negative document ID."""
        response = client.get("/api/v1/documents/-1/chunks")

        assert response.status_code == 422
