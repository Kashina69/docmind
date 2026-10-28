-- 016: add columns written by ingestion.py that were missing from 003.
-- doc_metadata (extraction info / error) and skipped_pages (image-only pages).

ALTER TABLE rag.documents
    ADD COLUMN IF NOT EXISTS doc_metadata JSONB DEFAULT '{}';

ALTER TABLE rag.documents
    ADD COLUMN IF NOT EXISTS skipped_pages JSONB DEFAULT '[]';

-- Drop the overloaded single-doc variants from 010/011 so PostgREST
-- has exactly one candidate for each RPC (013 multi-doc versions win).

DROP FUNCTION IF EXISTS rag.get_chunks_by_page(UUID, INT, INT, UUID);
DROP FUNCTION IF EXISTS rag.get_chunks_by_section(UUID, TEXT, UUID, INT);
