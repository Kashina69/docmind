import threading
from contextlib import asynccontextmanager

from app.ingestion import ingest_document
from app.supabase_client import get_service_client


def _recover_stuck_documents() -> None:
    try:
        stuck = get_service_client().schema("rag").table("documents") \
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


@asynccontextmanager
async def lifespan(_app):
    thread = threading.Thread(target=_recover_stuck_documents, daemon=True, name="resume-ingestions")
    thread.start()
    print("[Resume] Recovery thread started — server accepting traffic")
    yield
