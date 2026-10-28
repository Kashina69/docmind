from app.llm.client import _model as _llm_model
from app.llm.router import route_generation_model
from app.shared.rate_limiter import acquire_router_token


def route_model(r, query: str, n_docs: int) -> dict:
    if n_docs <= 1:
        return {"model": _llm_model("rag"), "name": "rag", "role": "rag", "token_used": False}

    if not acquire_router_token(r):
        print(f"[Handler] Router token unavailable — heuristic fallback → multi")
        return {"model": _llm_model("multi"), "name": "multi", "role": "multi", "token_used": False}

    role  = route_generation_model(query, n_docs)
    model = _llm_model(role)
    return {"model": model, "name": role, "role": role, "token_used": True}
