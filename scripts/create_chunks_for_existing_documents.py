#!/usr/bin/env python3
"""
Script to create/recreate chunks for existing documents.

Processes documents that have extracted_text, creating new chunks.
Deletes existing chunks first to support re-chunking with updated logic.

Usage:
    # Process all eligible documents (deletes existing chunks and recreates)
    python scripts/create_chunks_for_existing_documents.py

    # Preview without changes:
    python scripts/create_chunks_for_existing_documents.py --dry-run

Requirements:
    - Database must be running (docker-compose up -d postgres)
    - Virtual environment activated with dependencies installed
"""

import argparse
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import and_

from src.config.database import get_session_local
from src.models.database import Document, DocumentChunk
from src.preprocessing.chunking import TextChunker


def create_chunks_for_documents(dry_run: bool = False) -> None:
    """
    Create chunks for all documents with extracted text.

    Args:
        dry_run: If True, only print what would be done without making changes.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()

    total_documents = 0
    total_chunks_created = 0
    total_chunks_deleted = 0

    try:
        # Query documents with completed processing and extracted text
        documents = db.query(Document).filter(
            and_(
                Document.processing_status == "completed",
                Document.extracted_text.isnot(None)
            )
        ).all()

        if not documents:
            print("No documents found with processing_status='completed' and extracted_text.")
            return

        print(f"Found {len(documents)} document(s) to process.")
        if dry_run:
            print("DRY RUN MODE - No changes will be made.\n")
        print()

        chunker = TextChunker()

        for doc in documents:
            try:
                # Count/delete existing chunks
                existing_chunks = db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == doc.id
                ).count()

                if existing_chunks > 0:
                    if dry_run:
                        print(f"  Would delete {existing_chunks} existing chunks for document {doc.id}")
                    else:
                        db.query(DocumentChunk).filter(
                            DocumentChunk.document_id == doc.id
                        ).delete()
                    total_chunks_deleted += existing_chunks

                # Create new chunks
                chunk_records = chunker.chunk_to_db_records(
                    doc.extracted_text,
                    document_id=doc.id,
                    extra_metadata={"filename": doc.filename}
                )

                if not dry_run:
                    for record in chunk_records:
                        chunk = DocumentChunk(
                            document_id=record["document_id"],
                            chunk_index=record["chunk_index"],
                            content=record["content"],
                            chunk_metadata=record["metadata"],
                        )
                        db.add(chunk)
                    db.commit()

                total_documents += 1
                total_chunks_created += len(chunk_records)
                print(f"Processing document {doc.id} ({doc.filename}): {len(chunk_records)} chunks created")

            except Exception as e:
                print(f"Error processing document {doc.id}: {e}")
                if not dry_run:
                    db.rollback()
                continue

        # Print summary
        print()
        print("=" * 50)
        print("Summary:")
        print(f"  Documents processed: {total_documents}")
        print(f"  Chunks deleted: {total_chunks_deleted}")
        print(f"  Chunks created: {total_chunks_created}")
        if dry_run:
            print("  (DRY RUN - no actual changes made)")

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Create chunks for existing documents with extracted text."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be done without making changes"
    )
    args = parser.parse_args()

    create_chunks_for_documents(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
