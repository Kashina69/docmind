import hashlib
import json

from app.pipelines.query.history import save_assistant_message, update_conversation_timestamp
from app.shared.jobs import write_result as _write_result_job
from app.shared.supabase_client import get_service_client

CACHE_TTL = 3600

supabase = get_service_client()


def make_cache_key(user_id: str, query: str, doc_part: str, style: str) -> str:
    h = hashlib.sha256(query.lower().strip().encode()).hexdigest()
    return f"cache:{user_id}:{doc_part}:{style}:{h}"


def write_result(r, job_id: str, result: dict) -> None:
    _write_result_job(r, job_id, result)
    print(f"[Handler] Job result written: status={result.get('status')}")


def get_voice_credits(user_id: str) -> int:
    try:
        result = supabase \
            .schema("rag").table("user_profiles") \
            .select("voice_credits") \
            .eq("id", user_id) \
            .single() \
            .execute()
        return result.data.get("voice_credits", 0) if result.data else 0
    except Exception:
        return 0


def finish_job(
    r,
    job_id:           str,
    query:            str,
    answer:           str,
    user_id:          str,
    conversation_id:  str,
    voice_mode:       bool,
    retrieved_chunks: list[dict],
    cache_key:        str,
    tokens_used:      int = 0,
    path:             str = "rag",
) -> None:
    if path == "rag" and answer.startswith("This was not found in your documents."):
        path = "rag_fallback"

    save_assistant_message(
        conversation_id=conversation_id,
        user_id=user_id,
        content=answer,
        retrieved_chunks=retrieved_chunks,
        voice_url=None,
        voice_used=False,
    )

    update_conversation_timestamp(conversation_id)

    sources = [
        {
            "chunk_id":    c.get("id"),
            "document_id": c.get("document_id"),
            "page_number": c["metadata"].get("page_number"),
            "filename":    c["metadata"].get("filename"),
            "section":     c["metadata"].get("section"),
            "snippet":     c.get("content", ""),
        }
        for c in retrieved_chunks
    ]

    r.setex(cache_key, CACHE_TTL, json.dumps({"answer": answer, "sources": sources}))
    print(f"[Handler] Answer cached (TTL={CACHE_TTL}s)")

    write_result(r, job_id, {
        "status":                  "done",
        "answer":                  answer,
        "cached":                  False,
        "sources":                 sources,
        "voice_url":               None,
        "voice_urls":              None,
        "voice_credits_remaining": get_voice_credits(user_id),
        "tokens_used":             tokens_used,
        "path":                    path,
    })

    print(f"[Handler] Job {job_id} done "
          f"(path={path}, tokens={tokens_used})")
