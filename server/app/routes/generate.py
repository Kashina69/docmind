import json
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from app import flashcards, summarize
from app.rate_limiter import get_redis_client
from app.routes.deps import (
    VALID_TASK_TYPES,
    current_user,
    get_conversation,
    get_document,
    supabase,
)

router = APIRouter(tags=["generate"])


def _dispatch_generation(job_id, user_id, task_type, conversation_id, document_id, r) -> None:
    if task_type == "summarize_conversation":
        summarize.summarize_conversation(job_id, user_id, conversation_id, r)

    elif task_type == "summarize_document":
        summarize.summarize_document(job_id, user_id, document_id, r)

    elif task_type == "generate_flashcards":
        flashcards.generate_flashcards(job_id, user_id, conversation_id, document_id, r)

    else:
        from app.jobs import write_result
        write_result(r, job_id, {
            "status":  "error",
            "message": f"Unknown task_type: {task_type}",
        })


def _run_generation_with_retry(**kwargs) -> None:
    from app.jobs import write_result

    try:
        _dispatch_generation(**kwargs)
    except Exception as e:
        if "RATE_LIMIT_WAIT" not in str(e):
            raise
        print(f"[Generate] Rate limit wait — retrying once after 10s")
        time.sleep(10)
        try:
            _dispatch_generation(**kwargs)
        except Exception as e2:
            print(f"[Generate] Retry failed: {e2}")
            write_result(get_redis_client(), kwargs["job_id"], {
                "status": "error", "message": str(e2),
            })


@router.post("/generate")
async def post_generate(
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
):
    user = current_user(authorization)
    user_id = user["user_id"]

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "Bad Request", "message": "Invalid JSON in request body"})

    task_type       = (body.get("task_type") or "").strip()
    conversation_id = (body.get("conversation_id") or "").strip() or None
    document_id     = (body.get("document_id") or "").strip() or None

    if task_type not in VALID_TASK_TYPES:
        raise HTTPException(
            status_code=400,
            detail={"error": "Bad Request",
                    "message": f"task_type must be one of: {', '.join(sorted(VALID_TASK_TYPES))}"},
        )

    if task_type == "summarize_conversation" or (
        task_type == "generate_flashcards" and conversation_id
    ):
        if not conversation_id:
            raise HTTPException(status_code=400, detail={"error": "Bad Request", "message": "conversation_id is required for this task_type"})
        if not get_conversation(conversation_id, user_id):
            raise HTTPException(status_code=404, detail={"error": "Not Found", "message": "Conversation not found or does not belong to you"})

    if task_type == "summarize_document" or (
        task_type == "generate_flashcards" and document_id and not conversation_id
    ):
        if not document_id:
            raise HTTPException(status_code=400, detail={"error": "Bad Request", "message": "document_id is required for this task_type"})
        if not get_document(document_id, user_id):
            raise HTTPException(status_code=404, detail={"error": "Not Found", "message": "Document not found or does not belong to you"})

    r      = get_redis_client()
    job_id = str(uuid.uuid4())

    r.setex(f"job:{job_id}", 3600, json.dumps({"status": "pending"}))

    background_tasks.add_task(
        _run_generation_with_retry,
        job_id=job_id,
        user_id=user_id,
        task_type=task_type,
        conversation_id=conversation_id,
        document_id=document_id,
        r=r,
    )

    print(f"[Generate] Job {job_id} queued: task_type={task_type} user={user_id}")

    return {"job_id": job_id, "status": "pending"}


@router.get("/summaries")
def get_summaries(
    conversation_id: str = "",
    document_id: str = "",
    authorization: str | None = Header(default=None),
):
    user = current_user(authorization)
    user_id = user["user_id"]

    conversation_id = (conversation_id or "").strip() or None
    document_id     = (document_id or "").strip() or None

    if not conversation_id and not document_id:
        raise HTTPException(status_code=400, detail={"error": "Bad Request", "message": "conversation_id or document_id query parameter is required"})

    try:
        query = supabase().schema("rag").table("summaries") \
            .select("id, source_type, conversation_id, document_id, content, created_at") \
            .eq("user_id", user_id)

        if conversation_id:
            query = query.eq("conversation_id", conversation_id)
        else:
            query = query.eq("document_id", document_id)

        result = query.execute()
        return {"summaries": result.data or []}

    except Exception as e:
        print(f"[Summaries] Failed to fetch: {e}")
        raise HTTPException(status_code=500, detail={"error": "Internal Server Error", "message": "Failed to fetch summaries"})


@router.get("/flashcards")
def get_flashcards(
    conversation_id: str = "",
    document_id: str = "",
    deck_id: str = "",
    authorization: str | None = Header(default=None),
):
    user = current_user(authorization)
    user_id = user["user_id"]

    conversation_id = (conversation_id or "").strip() or None
    document_id     = (document_id or "").strip() or None
    deck_id         = (deck_id or "").strip() or None

    if not conversation_id and not document_id and not deck_id:
        raise HTTPException(
            status_code=400,
            detail={"error": "Bad Request",
                    "message": "One of conversation_id, document_id, or deck_id query parameter is required"},
        )

    try:
        deck_query = supabase().schema("rag").table("flashcard_decks") \
            .select("id, source_type, conversation_id, document_id, title, created_at") \
            .eq("user_id", user_id)

        if deck_id:
            deck_query = deck_query.eq("id", deck_id)
        elif conversation_id:
            deck_query = deck_query.eq("conversation_id", conversation_id)
        else:
            deck_query = deck_query.eq("document_id", document_id)

        decks_result = deck_query.execute()
        decks        = decks_result.data or []

        if not decks:
            return {"decks": []}

        deck_ids     = [d["id"] for d in decks]
        cards_result = supabase().schema("rag").table("flashcards") \
            .select("id, deck_id, question, answer") \
            .in_("deck_id", deck_ids) \
            .order("created_at") \
            .execute()

        cards_by_deck: dict[str, list] = {}
        for card in (cards_result.data or []):
            cards_by_deck.setdefault(card["deck_id"], []).append(card)

        for deck in decks:
            deck["cards"] = cards_by_deck.get(deck["id"], [])

        return {"decks": decks}

    except Exception as e:
        print(f"[Flashcards] Failed to fetch: {e}")
        raise HTTPException(status_code=500, detail={"error": "Internal Server Error", "message": "Failed to fetch flashcards"})
