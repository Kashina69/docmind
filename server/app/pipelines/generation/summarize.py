from app.shared.supabase_client import get_service_client
from app.shared.rate_limiter import acquire_task_token
from app.llm.client import generate, generate_json
from app.shared.jobs import write_result
from app.pipelines.generation.fetch import fetch_conversation_transcript, fetch_document, fetch_document_chunks

STUFF_THRESHOLD = 200_000

BATCH_CHARS = 15_000

MAX_CHUNKS = 500


def summarize_conversation(
    job_id:          str,
    user_id:         str,
    conversation_id: str,
    r,
) -> None:

    if not conversation_id:
        write_result(r, job_id, {"status": "error", "message": "conversation_id is required"})
        return

    supabase = get_service_client()

    messages, transcript = fetch_conversation_transcript(supabase, user_id, conversation_id)

    if not messages:
        write_result(r, job_id, {
            "status":  "error",
            "message": "Conversation has no messages to summarize",
        })
        return

    print(f"[Summarize] conversation={conversation_id}: "
          f"{len(messages)} messages, {len(transcript)} chars")

    acquired = acquire_task_token(r)
    if not acquired:
        raise Exception("RATE_LIMIT_WAIT")

    summary = generate([
        {
            "role":    "system",
            "content": (
                "Summarize the following conversation in 3-5 sentences. "
                "Capture the main topics discussed and any conclusions reached. "
                "Be concise and factual."
            ),
        },
        {
            "role":    "user",
            "content": transcript,
        },
    ])

    _persist_conversation_summary(supabase, user_id, conversation_id, summary)

    write_result(r, job_id, {
        "status":  "done",
        "summary": summary,
    })

    print(f"[Summarize] conversation={conversation_id} done ({len(summary)} chars)")


def _persist_conversation_summary(supabase, user_id, conversation_id, summary):
    supabase.schema("rag").table("summaries").upsert(
        {
            "user_id":         user_id,
            "source_type":     "conversation",
            "conversation_id": conversation_id,
            "document_id":     None,
            "content":         summary,
        },
        on_conflict="user_id,source_type,conversation_id,document_id",
    ).execute()

    supabase.schema("rag").table("conversations") \
        .update({"summary": summary}) \
        .eq("id", conversation_id) \
        .eq("user_id", user_id) \
        .execute()

    print(f"[Summarize] Persisted summary for conversation={conversation_id}")


def summarize_document(
    job_id:      str,
    user_id:     str,
    document_id: str,
    r,
) -> None:

    if not document_id:
        write_result(r, job_id, {"status": "error", "message": "document_id is required"})
        return

    supabase = get_service_client()

    doc = fetch_document(supabase, user_id, document_id)

    if not doc:
        write_result(r, job_id, {"status": "error", "message": "Document not found"})
        return

    if doc["status"] != "ready":
        write_result(r, job_id, {
            "status":  "error",
            "message": f"Document is not ready (status: {doc['status']})",
        })
        return

    chunks = fetch_document_chunks(supabase, user_id, document_id, limit=MAX_CHUNKS)

    if not chunks:
        write_result(r, job_id, {
            "status":  "error",
            "message": "Document has no chunks — re-index may be needed",
        })
        return

    total_chars = sum(len(c["content"]) for c in chunks)
    filename    = doc["filename"]

    print(f"[Summarize] document={document_id} ({filename}): "
          f"{len(chunks)} chunks, {total_chars} chars")

    if total_chars < STUFF_THRESHOLD:
        summary, strategy = _stuff_summarize(chunks, filename, r)
    else:
        summary, strategy = _map_reduce_summarize(chunks, filename, r)

    _persist_document_summary(supabase, user_id, document_id, summary)

    write_result(r, job_id, {
        "status":   "done",
        "summary":  summary,
        "strategy": strategy,
    })

    print(f"[Summarize] document={document_id} done "
          f"(strategy={strategy}, {len(summary)} chars)")


def _stuff_summarize(chunks: list[dict], filename: str, r) -> tuple[str, str]:
    content_block = "\n\n".join(c["content"] for c in chunks)

    acquired = acquire_task_token(r)
    if not acquired:
        raise Exception("RATE_LIMIT_WAIT")

    summary = generate([
        {
            "role":    "system",
            "content": (
                "Summarize the following document in clear, structured paragraphs. "
                "Cover the main topics, key findings, and any conclusions. "
                "Be thorough but concise."
            ),
        },
        {
            "role":    "user",
            "content": f"Document: {filename}\n\n{content_block}",
        },
    ], max_tokens=1024)

    return summary, "stuff"


def _map_reduce_summarize(chunks: list[dict], filename: str, r) -> tuple[str, str]:
    batches  = _make_batches(chunks, BATCH_CHARS)
    partials = []

    print(f"[Summarize] map-reduce: {len(batches)} batches for {filename}")

    for i, batch in enumerate(batches):
        acquired = acquire_task_token(r)
        if not acquired:
            raise Exception("RATE_LIMIT_WAIT")

        batch_text = "\n\n".join(c["content"] for c in batch)
        partial    = generate([
            {
                "role":    "system",
                "content": (
                    "Summarize the following excerpt in 3-5 sentences. "
                    "Focus on the key information presented."
                ),
            },
            {
                "role":    "user",
                "content": f"Excerpt {i + 1}/{len(batches)} from {filename}:\n\n{batch_text}",
            },
        ], max_tokens=512)

        partials.append(partial)
        print(f"[Summarize] map batch {i + 1}/{len(batches)} done")

    combined = "\n\n".join(f"Part {i + 1}: {p}" for i, p in enumerate(partials))

    acquired = acquire_task_token(r)
    if not acquired:
        raise Exception("RATE_LIMIT_WAIT")

    summary = generate([
        {
            "role":    "system",
            "content": (
                "You are given partial summaries of different sections of a document. "
                "Combine them into a single coherent summary covering the full document. "
                "Do not repeat information — synthesize it into clear paragraphs."
            ),
        },
        {
            "role":    "user",
            "content": f"Document: {filename}\n\nPartial summaries:\n\n{combined}",
        },
    ], max_tokens=1024)

    return summary, "map_reduce"


def _make_batches(chunks: list[dict], max_chars: int) -> list[list[dict]]:
    batches, current, current_chars = [], [], 0

    for chunk in chunks:
        chunk_len = len(chunk["content"])
        if current and current_chars + chunk_len > max_chars:
            batches.append(current)
            current, current_chars = [], 0
        current.append(chunk)
        current_chars += chunk_len

    if current:
        batches.append(current)

    return batches


def _persist_document_summary(supabase, user_id, document_id, summary):
    supabase.schema("rag").table("summaries").upsert(
        {
            "user_id":         user_id,
            "source_type":     "document",
            "conversation_id": None,
            "document_id":     document_id,
            "content":         summary,
        },
        on_conflict="user_id,source_type,conversation_id,document_id",
    ).execute()

    print(f"[Summarize] Persisted summary for document={document_id}")
