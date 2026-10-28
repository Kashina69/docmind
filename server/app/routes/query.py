import hashlib
import json
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.classifier import get_conversational_response
from app.jobs import read_result
from app.query_pipeline import run_query_pipeline
from app.rate_limiter import get_redis_client
from app.routes.deps import (
    current_user,
    get_conversation,
    make_cache_key,
    save_exchange,
)

router = APIRouter(tags=["query"])


def _run_query_with_retry(**kwargs) -> None:
    try:
        run_query_pipeline(**kwargs)
    except Exception as e:
        if "RATE_LIMIT_WAIT" not in str(e):
            raise
        print(f"[Query] Rate limit wait — retrying once after 10s")
        time.sleep(10)
        try:
            run_query_pipeline(**kwargs)
        except Exception as e2:
            print(f"[Query] Retry failed: {e2}")
            get_redis_client().setex(
                f"job:{kwargs['job_id']}", 3600,
                json.dumps({"status": "error", "message": str(e2)}),
            )


@router.post("/query")
async def post_query(
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

    query           = (body.get("question") or "").strip()
    conversation_id = (body.get("conversation_id") or "").strip()
    voice_mode      = body.get("voice_mode", False)
    response_style  = body.get("response_style", "explanatory")
    document_ids    = body.get("document_ids", [])

    if response_style not in {"concise", "explanatory", "conversational"}:
        response_style = "explanatory"

    if not query:
        raise HTTPException(status_code=400, detail={"error": "Bad Request", "message": "question field is required"})

    if not conversation_id:
        raise HTTPException(status_code=400, detail={"error": "Bad Request", "message": "conversation_id field is required"})

    if len(query) > 2000:
        raise HTTPException(status_code=400, detail={"error": "Bad Request", "message": "Question too long. Maximum 2000 characters."})

    print(f"[Submit] user={user_id} conversation={conversation_id} query='{query[:80]}'")

    conversational_response = get_conversational_response(query)

    if conversational_response:
        print(f"[Submit] Conversational query — instant response")

        save_exchange(
            conversation_id=conversation_id,
            user_id=user_id,
            user_message=query,
            assistant_message=conversational_response,
        )

        return {
            "job_id":      None,
            "status":      "done",
            "answer":      conversational_response,
            "cached":      False,
            "tokens_used": 0,
        }

    conversation = get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail={"error": "Not Found", "message": "Conversation not found or does not belong to you"})

    r         = get_redis_client()
    doc_part  = hashlib.sha256("|".join(sorted(document_ids)).encode()).hexdigest()[:12] if document_ids else (conversation.get("document_id") or "none")
    cache_key = make_cache_key(user_id, query, doc_part, response_style)
    cached_raw = r.get(cache_key)

    if cached_raw:
        print(f"[Submit] Cache hit — returning instantly")
        try:
            cached = json.loads(cached_raw)
            cached_answer = cached["answer"]
            cached_sources = cached.get("sources", [])
        except (json.JSONDecodeError, KeyError, TypeError):
            cached_answer = cached_raw
            cached_sources = []

        save_exchange(
            conversation_id=conversation_id,
            user_id=user_id,
            user_message=query,
            assistant_message=cached_answer,
        )

        return {
            "job_id":      None,
            "status":      "done",
            "answer":      cached_answer,
            "sources":     cached_sources,
            "cached":      True,
            "voice_url":   None,
            "voice_urls":  None,
            "tokens_used": 0,
        }

    job_id = str(uuid.uuid4())

    r.setex(f"job:{job_id}", 3600, json.dumps({"status": "pending"}))

    background_tasks.add_task(
        _run_query_with_retry,
        job_id=job_id,
        query=query,
        user_id=user_id,
        conversation_id=conversation_id,
        voice_mode=bool(voice_mode),
        response_style=response_style,
        document_ids=document_ids,
    )

    print(f"[Submit] Job {job_id} queued (background task)")

    return {"job_id": job_id, "status": "pending"}


@router.get("/result/{job_id}")
def get_result(job_id: str, authorization: str | None = Header(default=None)):
    user = current_user(authorization)

    print(f"[Poll] user={user['user_id']} job={job_id}")

    result = read_result(job_id)

    if result is None:
        raise HTTPException(status_code=404, detail={"status": "not_found"})

    return JSONResponse(status_code=200, content=result)
