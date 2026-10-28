import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import FileResponse

from app.ingestion import ingest_document
from app.storage import get_local_path, serve_url, storage_key_for
from app.routes.deps import current_user, supabase

router = APIRouter(tags=["upload"])


@router.post("/upload")
async def create_upload_url(request: Request, authorization: str | None = Header(default=None)):
    user = current_user(authorization)
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


@router.put("/ingest/{key:path}")
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


@router.post("/documents/upload")
async def upload_document_direct(
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
):
    user = current_user(authorization)
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

    supabase().schema("rag").table("documents").insert({
        "id": document_id,
        "user_id": user_id,
        "filename": filename,
        "s3_key": s3_key,
        "status": "processing",
    }).execute()

    background_tasks.add_task(ingest_document, document_id, user_id, filename, pdf_bytes)

    return {"status": "accepted", "document_id": document_id}


@router.get("/files/{key:path}")
def serve_file(key: str):
    path = get_local_path(key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail={"error": "Not Found", "message": "File not found"})
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@router.get("/document-url")
def get_document_url(document_id: str = "", authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    user_id = user["user_id"]

    document_id = (document_id or "").strip()
    if not document_id:
        raise HTTPException(status_code=400, detail={"error": "Bad Request", "message": "document_id query parameter is required"})

    try:
        result = supabase().schema("rag").table("documents") \
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
