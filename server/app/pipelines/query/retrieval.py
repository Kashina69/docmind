from app.shared.supabase_client import execute_hybrid_search, get_service_client

supabase = get_service_client()


def user_has_documents(user_id: str) -> bool:
    try:
        result = supabase.schema("rag").table("documents") \
            .select("id") \
            .eq("user_id", user_id) \
            .eq("status", "ready") \
            .limit(1) \
            .execute()
        return len(result.data) > 0
    except Exception as e:
        print(f"[Handler] _user_has_documents error: {e} — defaulting False")
        return False


def get_conversation_document_ids(conversation_id: str, user_id: str) -> list[str]:
    try:
        conv = supabase.schema("rag").table("conversations") \
            .select("id") \
            .eq("id", conversation_id) \
            .eq("user_id", user_id) \
            .single() \
            .execute()
        if not conv.data:
            return []
        result = supabase.schema("rag").table("conversation_documents") \
            .select("document_id") \
            .eq("conversation_id", conversation_id) \
            .execute()
        return [row["document_id"] for row in (result.data or [])]
    except Exception as e:
        print(f"[Handler] _get_conversation_document_ids error: {e}")
        return []


def get_conversation_document_id(conversation_id: str, user_id: str) -> str | None:
    try:
        result = supabase.schema("rag").table("conversations") \
            .select("document_id") \
            .eq("id", conversation_id) \
            .eq("user_id", user_id) \
            .single() \
            .execute()
        if not result.data:
            return None
        return result.data.get("document_id")
    except Exception as e:
        print(f"[Handler] _get_conversation_document_id error: {e}")
        return None


def hybrid_search(
    user_id: str,
    query_embedding: list[float],
    query_text: str,
    document_id: str | None,
    document_ids: list[str],
) -> list[dict]:
    if document_ids:
        results_obj = supabase.schema("rag").rpc("hybrid_search_multi_doc", {
            "query_embedding": query_embedding,
            "query_text": query_text,
            "target_user_id": user_id,
            "doc_ids": document_ids,
            "match_count": 20,
        }).execute()
        return results_obj.data or []
    return execute_hybrid_search(
        user_id=user_id,
        query_embedding=query_embedding,
        query_text=query_text,
        match_count=20,
        document_id=document_id,
    )


def get_chunks_by_page(
    user_id: str,
    page_number: int,
    document_id: str | None,
    document_ids: list[str] | None = None,
) -> list[dict]:
    params: dict = {
        "target_user_id": user_id,
        "target_page":    page_number,
        "match_count":    20,
    }
    if document_ids:
        params["target_doc_ids"] = document_ids
    else:
        params["target_doc_id"] = document_id
    result = supabase.schema("rag").rpc("get_chunks_by_page", params).execute()
    return result.data or []


def get_chunks_by_section(
    user_id: str,
    heading_pattern: str,
    document_id: str | None,
    document_ids: list[str] | None = None,
) -> list[dict]:
    params: dict = {
        "target_user_id":  user_id,
        "heading_pattern": heading_pattern,
        "match_count":     20,
    }
    if document_ids:
        params["target_doc_ids"] = document_ids
    else:
        params["target_doc_id"] = document_id
    result = supabase.schema("rag").rpc("get_chunks_by_section", params).execute()
    return result.data or []
