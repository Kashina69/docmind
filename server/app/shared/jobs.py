import json

from app.shared.rate_limiter import get_redis_client

RESULT_TTL = 3600


def write_result(r, job_id: str, result: dict) -> None:
    r.setex(f"job:{job_id}", RESULT_TTL, json.dumps(result))
    print(f"[Generation] Job result written: job={job_id} status={result.get('status')}")


def read_result(job_id: str) -> dict | None:
    r = get_redis_client()
    raw = r.get(f"job:{job_id}")
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "error", "message": "Invalid result format"}
