-- Add extraction columns to documents table
ALTER TABLE documents ADD COLUMN IF NOT EXISTS extracted_text TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS page_count INTEGER;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS extraction_error TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP;

-- Add index for processing queue queries
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status);
