from fastapi import APIRouter, Header, HTTPException

from app.routes.deps import current_user, supabase
from app.storage import delete_file

router = APIRouter(tags=["library"])


@router.get("/conversations")
def list_conversations(authorization: str | None = Header(default=None)):
    user = current_user(authorization)

    result = supabase().schema("rag").table("conversations") \
        .select("*, conversation_documents(document_id)") \
        .eq("user_id", user["user_id"]) \
        .order("updated_at", desc=True) \
        .execute()

    data = result.data or []
    mapped = [
        {**c, "documentIds": [cd["document_id"] for cd in (c.get("conversation_documents") or [])]}
        for c in data
    ]
    return mapped


@router.delete("/documents/{document_id}")
def delete_document(document_id: str, authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    user_id = user["user_id"]

    if not document_id.strip():
        raise HTTPException(status_code=400, detail={"error": "documentId path parameter is required"})

    print(f"[Delete] user={user_id} document={document_id}")

    result = (
        supabase()
        .schema("rag").table("documents")
        .select("id, s3_key, status")
        .eq("id", document_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail={"error": "Document not found"})

    delete_file(result.data["s3_key"])

    (
        supabase()
        .schema("rag").table("documents")
        .delete()
        .eq("id", document_id)
        .eq("user_id", user_id)
        .execute()
    )

    print(f"[Delete] Document {document_id} deleted")
    return {"deleted": True, "document_id": document_id}


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    user_id = user["user_id"]

    if not conversation_id.strip():
        raise HTTPException(status_code=400, detail={"error": "conversationId path parameter is required"})

    print(f"[Delete] user={user_id} conversation={conversation_id}")

    conv = (
        supabase()
        .schema("rag").table("conversations")
        .select("id")
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )

    if not conv.data:
        raise HTTPException(status_code=404, detail={"error": "Conversation not found"})

    (
        supabase()
        .schema("rag").table("conversations")
        .delete()
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .execute()
    )

    print(f"[Delete] Conversation {conversation_id} deleted")
    return {"deleted": True, "conversation_id": conversation_id}
