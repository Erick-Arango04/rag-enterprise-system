import pytest
from fastapi.testclient import TestClient


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
        assert "Invalid file type" in response.json()["detail"]

    def test_upload_large_file_returns_413(self, client, sample_large_file):
        """POST /upload with >50MB file returns 413."""
        filename, content, content_type = sample_large_file
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )

        assert response.status_code == 413
        assert "File too large" in response.json()["detail"]

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
        assert "Storage service is currently unavailable" in response.json()["detail"]

    # Response validation
    def test_error_response_has_detail(self, client, sample_invalid_file):
        """Error responses contain 'detail' field."""
        filename, content, content_type = sample_invalid_file
        response = client.post(
            "/api/v1/upload",
            files={"file": (filename, content, content_type)},
        )

        assert "detail" in response.json()


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
        assert "Document not found" in response.json()["detail"]

    def test_get_document_invalid_id_returns_422(self, client):
        """GET /documents/{id} returns 422 for invalid document ID."""
        response = client.get("/api/v1/documents/0")

        assert response.status_code == 422

    def test_get_document_negative_id_returns_422(self, client):
        """GET /documents/{id} returns 422 for negative document ID."""
        response = client.get("/api/v1/documents/-1")

        assert response.status_code == 422
