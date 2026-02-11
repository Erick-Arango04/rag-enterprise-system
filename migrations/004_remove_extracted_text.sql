-- Migration: Remove extracted_text column from documents table
-- This column is no longer needed as text content is now stored only in chunks
-- Date: 2026-02-04

ALTER TABLE documents DROP COLUMN IF EXISTS extracted_text;
