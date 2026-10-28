from supabase import create_client, Client
from app.secrets import get_secret

_service_client: Client | None = None


def get_service_client() -> Client:
    global _service_client

    if _service_client is None:
        supabase_url = get_secret("SUPABASE_URL")
        service_key  = get_secret("SUPABASE_SERVICE_KEY")

        _service_client = create_client(supabase_url, service_key)
        print("Supabase service client initialised")

    return _service_client


def get_user_client(user_jwt: str) -> Client:
    supabase_url = get_secret("SUPABASE_URL")
    anon_key     = get_secret("SUPABASE_ANON_KEY")

    client = create_client(supabase_url, anon_key)

    client.auth.set_session(
        access_token=user_jwt,
        refresh_token=""
    )

    return client


def execute_hybrid_search(
    user_id:         str,
    query_embedding: list[float],
    query_text:      str,
    match_count:     int = 10,
    document_id:     str | None = None,
) -> list[dict]:
    client = get_service_client()

    if document_id:
        result = client.schema("rag").rpc(
            "hybrid_search_in_document",
            {
                "query_embedding":    query_embedding,
                "query_text":         query_text,
                "target_user_id":     user_id,
                "target_document_id": document_id,
                "match_count":        match_count,
            }
        ).execute()
    else:
        result = client.schema("rag").rpc(
            "hybrid_search",
            {
                "query_embedding": query_embedding,
                "query_text":      query_text,
                "target_user_id":  user_id,
                "match_count":     match_count,
            }
        ).execute()

    return result.data


def consume_voice_credit(user_id: str) -> bool:
    client = get_service_client()

    result = client.schema("rag").rpc(
        "consume_voice_credit",
        {"target_user_id": user_id}
    ).execute()

    return result.data


def refund_voice_credit(user_id: str) -> None:
    client = get_service_client()
    client.schema("rag").rpc(
        "refund_voice_credit",
        {"target_user_id": user_id}
    ).execute()
