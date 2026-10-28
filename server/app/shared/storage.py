import os
from pathlib import Path

STORAGE_ROOT = Path(os.getenv("STORAGE_DIR", "storage"))


def storage_key_for(user_id: str, document_id: str, filename: str) -> str:
    return f"uploads/{user_id}/{document_id}/{filename}"


def put_file(key: str, data: bytes, content_type: str = "application/octet-stream") -> Path:
    dest = STORAGE_ROOT / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f"[Storage] Wrote {len(data)} bytes → {dest}")
    return dest


def delete_file(key: str) -> None:
    dest = STORAGE_ROOT / key
    try:
        dest.unlink(missing_ok=True)
        print(f"[Storage] Deleted {dest}")
    except Exception as e:
        print(f"[Storage] Warning: delete failed for {dest}: {e}")


def get_local_path(key: str) -> Path:
    return STORAGE_ROOT / key


def serve_url(app_base_url: str, key: str) -> str:
    return f"{app_base_url.rstrip('/')}/files/{key}"
