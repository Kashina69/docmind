import hashlib

from fastapi import HTTPException

from app.auth import get_user_from_token
from app.supabase_client import get_service_client

CACHE_TTL = 3600

VALID_TASK_TYPES = {"summarize_conversation", "summarize_document", "generate_flashcards"}


def current_user(authorization: str | None) -> dict:
    try:
        return get_user_from_token(authorization)
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail={"error": "Unauthorized", "message": str(e)},
        )


def supabase():
    return get_service_client()


def get_conversation(conversation_id: str, user_id: str) -> dict | None:
    try:
        result = supabase().schema("rag") \
            .table("conversations") \
            .select("id, document_id") \
            .eq("id", conversation_id) \
            .eq("user_id", user_id) \
            .single() \
            .execute()
        return result.data
    except Exception:
        return None


def get_document(document_id: str, user_id: str) -> dict | None:
    try:
        result = supabase().schema("rag") \
            .table("documents") \
            .select("id, filename, status") \
            .eq("id", document_id) \
            .eq("user_id", user_id) \
            .eq("status", "ready") \
            .single() \
            .execute()
        return result.data
    except Exception:
        return None


def save_exchange(
    conversation_id: str,
    user_id: str,
    user_message: str,
    assistant_message: str,
) -> None:
    try:
        supabase().schema("rag").table("messages").insert([
            {
                "conversation_id": conversation_id,
                "user_id":         user_id,
                "role":            "user",
                "content":         user_message,
                "voice_used":      False,
            },
            {
                "conversation_id":  conversation_id,
                "user_id":          user_id,
                "role":             "assistant",
                "content":          assistant_message,
                "retrieved_chunks": [],
                "voice_used":       False,
            },
        ]).execute()

        supabase().schema("rag") \
            .table("conversations") \
            .update({"updated_at": "NOW()"}) \
            .eq("id", conversation_id) \
            .execute()

        print(f"[Submit] Exchange saved to {conversation_id}")

    except Exception as e:
        print(f"[Submit] Warning: failed to save exchange: {e}")


def make_cache_key(user_id: str, query: str, doc_part: str, style: str) -> str:
    h = hashlib.sha256(query.lower().strip().encode()).hexdigest()
    return f"cache:{user_id}:{doc_part}:{style}:{h}"
