import hashlib
import os
from pathlib import Path

from app.chunker import chunk_pages
from app.embedder import embed_texts
from app.extractor import read_pdf_bytes, extract_text_from_pdf
from app.storage import storage_key_for, put_file, get_local_path
from app.supabase_client import get_service_client

EMBED_BATCH_SIZE  = 32

supabase = get_service_client()

STORAGE_ROOT = Path(os.getenv("STORAGE_DIR", "storage"))


def ingest_document(document_id: str, user_id: str, filename: str, pdf_bytes: bytes | None = None) -> None:
    s3_key = f"uploads/{user_id}/{document_id}/{filename}"
    print(f"[Ingest] document={document_id} user={user_id} file={filename}")

    _update_document(document_id, {"status": "processing"})

    deleted = supabase.schema("rag").table("chunks") \
        .delete() \
        .eq("document_id", document_id) \
        .execute()
    print(f"[Ingest] Cleared {len(deleted.data or [])} stale chunk(s) — clean start")

    try:
        if pdf_bytes is None:
            pdf_bytes = get_local_path(s3_key).read_bytes()
            print(f"[Ingest] Resumed — loaded {len(pdf_bytes)} bytes from local storage")
        put_file(s3_key, pdf_bytes, "application/pdf")

        extraction   = extract_text_from_pdf(pdf_bytes, s3_key, filename)
        pages        = extraction["pages"]
        doc_metadata = extraction["document_metadata"]
        skipped      = extraction["skipped_pages"]
        del pdf_bytes

        print(f"[Ingest] Extracted {len(pages)} pages, {len(skipped)} skipped")

        chunks = chunk_pages(pages)

        chunks = _deduplicate(chunks)

        print(f"[Ingest] {len(chunks)} chunks — storing...")

        rows = [
            {
                "document_id": document_id,
                "user_id":     user_id,
                "content":     c["content"],
                "embedding":   None,
                "metadata":    c["metadata"],
            }
            for c in chunks
        ]

        chunk_ids: list[str] = []
        for i in range(0, len(rows), 100):
            batch = rows[i: i + 100]
            result = (
                supabase
                .schema("rag").table("chunks")
                .insert(batch)
                .execute()
            )
            ids = [row["id"] for row in result.data]
            chunk_ids.extend(ids)
            print(f"[Ingest] Stored batch {i // 100 + 1} — {len(ids)} chunks")

        print(f"[Ingest] Stored {len(chunk_ids)} chunks — embedding...")

        for i in range(0, len(chunk_ids), EMBED_BATCH_SIZE):
            batch_ids = chunk_ids[i: i + EMBED_BATCH_SIZE]

            result = supabase.schema("rag").table("chunks") \
                .select("id, content") \
                .in_("id", batch_ids) \
                .execute()

            fetched = result.data or []
            texts = [c["content"] for c in fetched]
            ids   = [c["id"] for c in fetched]

            embeddings = embed_texts(texts)

            for chunk_id, embedding in zip(ids, embeddings):
                supabase.schema("rag").table("chunks") \
                    .update({"embedding": embedding}) \
                    .eq("id", chunk_id) \
                    .execute()

            print(f"[Ingest] Embedded batch {i // EMBED_BATCH_SIZE + 1} "
                  f"({len(embeddings)} chunks)")

        _update_document(document_id, {
            "status":        "ready",
            "chunk_count":   len(chunk_ids),
            "skipped_pages": skipped,
            "doc_metadata":  doc_metadata,
        })

        print(f"[Ingest] document={document_id} chunks={len(chunk_ids)} status=ready")

    except ValueError as e:
        print(f"[Ingest] PDF error: {e}")
        _update_document(document_id, {
            "status": "failed",
            "doc_metadata": {"error": str(e)},
        })
        raise

    except Exception as e:
        print(f"[Ingest] Unrecoverable: {e}")
        _update_document(document_id, {
            "status": "failed",
            "doc_metadata": {"error": str(e)},
        })
        raise


def _deduplicate(chunks: list[dict]) -> list[dict]:
    seen:   set[str]   = set()
    result: list[dict] = []
    for chunk in chunks:
        h = hashlib.md5(chunk["content"].encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            result.append(chunk)
    return result


def _update_document(document_id: str, fields: dict) -> None:
    supabase \
        .schema("rag").table("documents") \
        .update(fields) \
        .eq("id", document_id) \
        .execute()
    status = fields.get("status", "")
    print(f"[Ingest] Document updated"
          + (f" → {status}" if status else ""))
