import hashlib
import json
import time
import uuid

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app import flashcards, summarize
from app.auth import get_user_from_token
from app.ingestion import ingest_document
from app.jobs import read_result
from app.query_pipeline import run_query_pipeline
from app.rate_limiter import get_redis_client
from app.classifier import get_conversational_response
from app.storage import delete_file, get_local_path, put_file, serve_url, storage_key_for
from app.supabase_client import get_service_client

CACHE_TTL = 3600

VALID_TASK_TYPES = {"summarize_conversation", "summarize_document", "generate_flashcards"}

app = FastAPI(title="DocMind API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _resume_interrupted_ingestions() -> None:
    import threading

    def _run() -> None:
        try:
            stuck = _supabase().schema("rag").table("documents") \
                .select("id, user_id, filename") \
                .in_("status", ["processing", "indexing"]) \
                .execute().data or []
        except Exception as e:
            print(f"[Resume] Could not list stuck documents: {e}")
            return
        if not stuck:
            print("[Resume] No stuck documents")
            return
        print(f"[Resume] {len(stuck)} stuck document(s) — re-ingesting in background")
        for doc in stuck:
            try:
                ingest_document(doc["id"], doc["user_id"], doc["filename"])
            except Exception as e:
                print(f"[Resume] document={doc['id']} still failing: {e}")

    thread = threading.Thread(target=_run, daemon=True, name="resume-ingestions")
    thread.start()
    print("[Resume] Recovery thread started — server accepting traffic")


def _auth(authorization: str | None) -> dict:
    try:
        return get_user_from_token(authorization)
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail={"error": "Unauthorized", "message": str(e)},
        )


def _supabase():
    return get_service_client()


@app.get("/")
def health():
    return {"status": "ok"}


# ── Upload ─────────────────────────────────────────────────────────────

@app.post("/upload")
async def create_upload_url(request: Request, authorization: str | None = Header(default=None)):
    from app.secrets import get_secret as _get_secret
    import os

    user = _auth(authorization)
    user_id = user["user_id"]

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "Bad Request", "message": "Invalid JSON"})

    filename    = (body.get("filename") or "").strip()
    document_id = (body.get("document_id") or "").strip() or str(uuid.uuid4())

    if not filename:
        raise HTTPException(status_code=400, detail={"error": "Bad Request", "message": "filename field is required"})

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail={"error": "Bad Request", "message": "Only PDF files are supported"})

    s3_key = storage_key_for(user_id, document_id, filename)
    base = os.getenv("APP_BASE_URL", "http://localhost:8000")

    print(f"[Upload] Upload slot: user={user_id} document={document_id} file={filename}")

    return {
        "upload_url":  f"{base.rstrip('/')}/ingest/{s3_key}",
        "s3_key":      s3_key,
        "document_id": document_id,
        "expires_in":  900,
    }


@app.put("/ingest/{key:path}")
async def ingest_upload(key: str, request: Request, background_tasks: BackgroundTasks):
    parts = key.split("/")
    if len(parts) < 4 or parts[0] != "uploads":
        raise HTTPException(status_code=400, detail={"error": "Bad Request", "message": "Invalid storage key"})

    user_id     = parts[1]
    document_id = parts[2]
    filename    = "/".join(parts[3:])

    pdf_bytes = await request.body()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail={"error": "Bad Request", "message": "Empty upload body"})

    print(f"[Upload] Received {len(pdf_bytes)} bytes for document={document_id}")

    background_tasks.add_task(ingest_document, document_id, user_id, filename, pdf_bytes)

    return {"status": "accepted", "document_id": document_id}


@app.post("/documents/upload")
async def upload_document_direct(
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
):
    user = _auth(authorization)
    user_id = user["user_id"]

    form = await request.form()
    upload = form.get("file")
    if upload is None:
        raise HTTPException(status_code=400, detail={"error": "Bad Request", "message": "file field is required"})

    filename = upload.filename or "document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail={"error": "Bad Request", "message": "Only PDF files are supported"})

    document_id = str(uuid.uuid4())
    pdf_bytes = await upload.read()

    s3_key = storage_key_for(user_id, document_id, filename)

    _supabase().schema("rag").table("documents").insert({
        "id": document_id,
        "user_id": user_id,
        "filename": filename,
        "s3_key": s3_key,
        "status": "processing",
    }).execute()

    background_tasks.add_task(ingest_document, document_id, user_id, filename, pdf_bytes)

    return {"status": "accepted", "document_id": document_id}


@app.get("/files/{key:path}")
def serve_file(key: str):
    path = get_local_path(key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail={"error": "Not Found", "message": "File not found"})
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@app.get("/document-url")
def get_document_url(document_id: str = "", authorization: str | None = Header(default=None)):
    import os

    user = _auth(authorization)
    user_id = user["user_id"]

    document_id = (document_id or "").strip()
    if not document_id:
        raise HTTPException(status_code=400, detail={"error": "Bad Request", "message": "document_id query parameter is required"})

    try:
        result = _supabase().schema("rag").table("documents") \
            .select("id, s3_key, filename, status") \
            .eq("id", document_id) \
            .eq("user_id", user_id) \
            .single() \
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail={"error": "Not Found", "message": "Document not found"})

        document = result.data

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail={"error": "Not Found", "message": "Document not found"})

    if document["status"] != "ready":
        raise HTTPException(
            status_code=400,
            detail={"error": "Bad Request",
                    "message": f"Document is not ready yet (status: {document['status']})"},
        )

    base = os.getenv("APP_BASE_URL", "http://localhost:8000")

    print(f"[DocumentURL] Serving local file for document={document_id} user={user_id}")

    return {
        "document_url": serve_url(base, document["s3_key"]),
        "filename":     document["filename"],
        "document_id":  document_id,
        "expires_in":   3600,
    }


# ── Query ──────────────────────────────────────────────────────────────

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


@app.post("/query")
async def post_query(
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
):
    user = _auth(authorization)
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

        _save_exchange(
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

    conversation = _get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail={"error": "Not Found", "message": "Conversation not found or does not belong to you"})

    r         = get_redis_client()
    doc_part  = hashlib.sha256("|".join(sorted(document_ids)).encode()).hexdigest()[:12] if document_ids else (conversation.get("document_id") or "none")
    cache_key = _make_cache_key(user_id, query, doc_part, response_style)
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

        _save_exchange(
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


@app.get("/result/{job_id}")
def get_result(job_id: str, authorization: str | None = Header(default=None)):
    user = _auth(authorization)

    print(f"[Poll] user={user['user_id']} job={job_id}")

    result = read_result(job_id)

    if result is None:
        raise HTTPException(status_code=404, detail={"status": "not_found"})

    return JSONResponse(status_code=200, content=result)


# ── Generate (summaries + flashcards) ──────────────────────────────────

def _run_generation_with_retry(**kwargs) -> None:
    from app.jobs import write_result

    task_type = kwargs.get("task_type")
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


@app.post("/generate")
async def post_generate(
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
):
    user = _auth(authorization)
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
        if not _get_conversation(conversation_id, user_id):
            raise HTTPException(status_code=404, detail={"error": "Not Found", "message": "Conversation not found or does not belong to you"})

    if task_type == "summarize_document" or (
        task_type == "generate_flashcards" and document_id and not conversation_id
    ):
        if not document_id:
            raise HTTPException(status_code=400, detail={"error": "Bad Request", "message": "document_id is required for this task_type"})
        if not _get_document(document_id, user_id):
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


@app.get("/summaries")
def get_summaries(
    conversation_id: str = "",
    document_id: str = "",
    authorization: str | None = Header(default=None),
):
    user = _auth(authorization)
    user_id = user["user_id"]

    conversation_id = (conversation_id or "").strip() or None
    document_id     = (document_id or "").strip() or None

    if not conversation_id and not document_id:
        raise HTTPException(status_code=400, detail={"error": "Bad Request", "message": "conversation_id or document_id query parameter is required"})

    try:
        query = _supabase().schema("rag").table("summaries") \
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


@app.get("/flashcards")
def get_flashcards(
    conversation_id: str = "",
    document_id: str = "",
    deck_id: str = "",
    authorization: str | None = Header(default=None),
):
    user = _auth(authorization)
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
        deck_query = _supabase().schema("rag").table("flashcard_decks") \
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
        cards_result = _supabase().schema("rag").table("flashcards") \
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


# ── Delete ─────────────────────────────────────────────────────────────

@app.get("/conversations")
def list_conversations(authorization: str | None = Header(default=None)):
    user = _auth(authorization)

    result = _supabase().schema("rag").table("conversations") \
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


@app.delete("/documents/{document_id}")
def delete_document(document_id: str, authorization: str | None = Header(default=None)):
    user = _auth(authorization)
    user_id = user["user_id"]

    if not document_id.strip():
        raise HTTPException(status_code=400, detail={"error": "documentId path parameter is required"})

    print(f"[Delete] user={user_id} document={document_id}")

    result = (
        _supabase()
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
        _supabase()
        .schema("rag").table("documents")
        .delete()
        .eq("id", document_id)
        .eq("user_id", user_id)
        .execute()
    )

    print(f"[Delete] Document {document_id} deleted")
    return {"deleted": True, "document_id": document_id}


@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, authorization: str | None = Header(default=None)):
    user = _auth(authorization)
    user_id = user["user_id"]

    if not conversation_id.strip():
        raise HTTPException(status_code=400, detail={"error": "conversationId path parameter is required"})

    print(f"[Delete] user={user_id} conversation={conversation_id}")

    conv = (
        _supabase()
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
        _supabase()
        .schema("rag").table("conversations")
        .delete()
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .execute()
    )

    print(f"[Delete] Conversation {conversation_id} deleted")
    return {"deleted": True, "conversation_id": conversation_id}


# ── Shared helpers (same logic as submit handler) ──────────────────────

def _get_conversation(conversation_id: str, user_id: str) -> dict | None:
    try:
        result = _supabase().schema("rag") \
            .table("conversations") \
            .select("id, document_id") \
            .eq("id", conversation_id) \
            .eq("user_id", user_id) \
            .single() \
            .execute()
        return result.data
    except Exception:
        return None


def _get_document(document_id: str, user_id: str) -> dict | None:
    try:
        result = _supabase().schema("rag") \
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


def _save_exchange(
    conversation_id:   str,
    user_id:           str,
    user_message:      str,
    assistant_message: str,
) -> None:
    try:
        _supabase().schema("rag").table("messages").insert([
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

        _supabase().schema("rag") \
            .table("conversations") \
            .update({"updated_at": "NOW()"}) \
            .eq("id", conversation_id) \
            .execute()

        print(f"[Submit] Exchange saved to {conversation_id}")

    except Exception as e:
        print(f"[Submit] Warning: failed to save exchange: {e}")


def _make_cache_key(user_id: str, query: str, doc_part: str, style: str) -> str:
    h = hashlib.sha256(query.lower().strip().encode()).hexdigest()
    return f"cache:{user_id}:{doc_part}:{style}:{h}"
