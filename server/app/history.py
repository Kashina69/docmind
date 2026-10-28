from app.supabase_client import get_service_client

HISTORY_PAIRS = 3


def fetch_conversation_history(
    conversation_id: str,
    user_id:         str,
) -> list[dict]:
    supabase = get_service_client()

    result = supabase \
        .schema("rag").table("messages") \
        .select("role, content") \
        .eq("conversation_id", conversation_id) \
        .eq("user_id", user_id) \
        .order("created_at", desc=True) \
        .limit(HISTORY_PAIRS * 2) \
        .execute()

    if not result.data:
        print(f"[History] No history found for "
              f"conversation {conversation_id}")
        return []

    messages = list(reversed(result.data))

    print(f"[History] Loaded {len(messages)} messages "
          f"from conversation {conversation_id}")

    return messages


def save_user_message(
    conversation_id: str,
    user_id:         str,
    content:         str,
) -> None:
    supabase = get_service_client()

    supabase \
        .schema("rag").table("messages") \
        .insert({
            "conversation_id": conversation_id,
            "user_id":         user_id,
            "role":            "user",
            "content":         content,
            "voice_used":      False,
        }) \
        .execute()

    print(f"[History] Saved user message to "
          f"conversation {conversation_id}")


def save_assistant_message(
    conversation_id:  str,
    user_id:          str,
    content:          str,
    retrieved_chunks: list[dict] = None,
    voice_url:        str        = None,
    voice_used:       bool       = False,
) -> None:
    supabase = get_service_client()

    chunks_for_storage = [
        {
            "id":          chunk.get("id"),
            "document_id": chunk.get("document_id"),
            "content":     chunk.get("content"),
            "page_number": chunk.get("metadata", {}).get("page_number"),
            "filename":    chunk.get("metadata", {}).get("filename"),
            "section":     chunk.get("metadata", {}).get("section"),
            "rrf_score":   chunk.get("rrf_score"),
        }
        for chunk in (retrieved_chunks or [])
    ]

    supabase \
        .schema("rag").table("messages") \
        .insert({
            "conversation_id":  conversation_id,
            "user_id":          user_id,
            "role":             "assistant",
            "content":          content,
            "retrieved_chunks": chunks_for_storage,
            "voice_url":        voice_url,
            "voice_used":       voice_used,
        }) \
        .execute()

    print(f"[History] Saved assistant message "
          f"({len(chunks_for_storage)} chunks stored) "
          f"to conversation {conversation_id}")


def update_conversation_timestamp(conversation_id: str) -> None:
    supabase = get_service_client()

    supabase \
        .schema("rag").table("conversations") \
        .update({"updated_at": "NOW()"}) \
        .eq("id", conversation_id) \
        .execute()
