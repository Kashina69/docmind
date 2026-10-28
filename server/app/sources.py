def fetch_conversation_messages(supabase, user_id: str, conversation_id: str, role: str | None = None) -> list[dict]:
    q = supabase.schema("rag").table("messages") \
        .select("role, content") \
        .eq("conversation_id", conversation_id) \
        .eq("user_id", user_id) \
        .order("created_at", desc=False)
    if role is not None:
        q = q.eq("role", role)
    result = q.execute()
    return result.data or []


def fetch_conversation_transcript(supabase, user_id: str, conversation_id: str, role: str | None = None) -> tuple[list[dict], str]:
    messages = fetch_conversation_messages(supabase, user_id, conversation_id, role)
    transcript = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in messages
    )
    return messages, transcript


def fetch_document_chunks(
    supabase,
    user_id: str,
    document_id: str,
    limit: int = 500,
    select: str = "content, metadata",
) -> list[dict]:
    result = supabase.schema("rag").table("chunks") \
        .select(select) \
        .eq("document_id", document_id) \
        .eq("user_id", user_id) \
        .order("metadata->>chunk_index") \
        .limit(limit) \
        .execute()
    return result.data or []


def fetch_document(supabase, user_id: str, document_id: str) -> dict | None:
    result = supabase.schema("rag").table("documents") \
        .select("id, filename, status") \
        .eq("id", document_id) \
        .eq("user_id", user_id) \
        .single() \
        .execute()
    return result.data


def fetch_source_content(
    supabase,
    user_id:         str,
    conversation_id: str | None,
    document_id:     str | None,
    chunk_limit:     int = 100,
) -> tuple[str, str, str]:
    if conversation_id:
        messages = fetch_conversation_messages(supabase, user_id, conversation_id, role="assistant")
        content  = "\n\n".join(m["content"] for m in messages)
        return content, "conversation", conversation_id

    doc = fetch_document(supabase, user_id, document_id)
    if not doc or doc["status"] != "ready":
        return "", "document", document_id

    chunks  = fetch_document_chunks(supabase, user_id, document_id, limit=chunk_limit, select="content")
    content = "\n\n".join(c["content"] for c in chunks)
    return content, "document", document_id
