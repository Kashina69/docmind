import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor

from app.supabase_client import get_service_client, execute_hybrid_search
from app.rate_limiter import (
    get_redis_client,
    acquire_router_token,
    acquire_hyde_token,
    acquire_generate_tokens,
    get_rate_limit_snapshot,
    GENERATE_COST,
    HYDE_COST,
)
from app.classifier import get_conversational_response
from app.hyde import generate_hyde_embedding, embed_query
from app.mmr import mmr_rerank
from app.generation import generate_answer, direct_answer
from app.router import needs_retrieval, rewrite_query, route_generation_model
from app.llm import _model as _llm_model
from app.history import (
    fetch_conversation_history,
    save_user_message,
    save_assistant_message,
    update_conversation_timestamp,
)
from app.jobs import write_result as _write_result_job

RESULT_TTL  = 3600
CACHE_TTL   = 3600
TTS_MAX_CHARS = 500

HYDE_CONFIDENCE_THRESHOLD = 0.02

MIN_USEFUL_RRF_SCORE = 0.005

MMR_TOP_K  = 5
MMR_LAMBDA = 0.7

supabase = get_service_client()


def run_query_pipeline(
    job_id:          str,
    query:           str,
    user_id:         str,
    conversation_id: str,
    voice_mode:      bool = False,
    response_style:  str = "explanatory",
    document_ids:    list[str] | None = None,
) -> None:
    r        = get_redis_client()
    snapshot = get_rate_limit_snapshot(r)
    print(f"[Handler] Token buckets: {snapshot}")

    document_ids = document_ids or []
    with ThreadPoolExecutor(max_workers=2) as ex:
        ids_future = (
            ex.submit(_get_conversation_document_ids, conversation_id, user_id)
            if not document_ids else None
        )
        id_future = ex.submit(_get_conversation_document_id, conversation_id, user_id)
        if ids_future is not None:
            document_ids = ids_future.result()
        document_id = id_future.result()

    print(f"[Handler] Job {job_id}: '{query[:80]}'")

    try:
        conversational_response = get_conversational_response(query)

        if conversational_response:
            print(f"[Handler] Conversational — instant (0 tokens)")
            save_user_message(conversation_id, user_id, query)
            save_assistant_message(
                conversation_id=conversation_id,
                user_id=user_id,
                content=conversational_response,
                retrieved_chunks=[],
            )
            update_conversation_timestamp(conversation_id)
            _write_result(r, job_id, {
                "status":                  "done",
                "answer":                  conversational_response,
                "cached":                  False,
                "voice_url":               None,
                "voice_credits_remaining": _get_voice_credits(user_id),
                "tokens_used":             0,
                "path":                    "conversational",
            })
            return

        doc_part  = hashlib.sha256("|".join(sorted(document_ids)).encode()).hexdigest()[:12] if document_ids else (document_id or "none")
        cache_key = _make_cache_key(user_id, query, doc_part, response_style)
        cached_raw = r.get(cache_key)

        if cached_raw:
            print(f"[Handler] Cache hit — 0 tokens consumed")
            try:
                cached = json.loads(cached_raw)
                cached_answer = cached["answer"]
                cached_sources = cached.get("sources", [])
            except (json.JSONDecodeError, KeyError, TypeError):
                cached_answer = cached_raw
                cached_sources = []
            _write_result(r, job_id, {
                "status":                  "done",
                "answer":                  cached_answer,
                "sources":                 cached_sources,
                "cached":                  True,
                "voice_url":               None,
                "voice_urls":              None,
                "voice_credits_remaining": _get_voice_credits(user_id),
                "tokens_used":             0,
                "path":                    "cache",
            })
            return

        with ThreadPoolExecutor(max_workers=3) as ex:
            save_future     = ex.submit(save_user_message, conversation_id, user_id, query)
            history_future  = ex.submit(fetch_conversation_history, conversation_id, user_id)
            has_docs_future = ex.submit(_user_has_documents, user_id)

            history = history_future.result()
            save_future.result()

            search_query  = rewrite_query(query, history)
            user_has_docs = has_docs_future.result()

        tokens_used = 0

        if not user_has_docs:
            print(f"[Handler] No ready documents — using LLM router")

            router_acquired = acquire_router_token(r)
            if not router_acquired:
                print(f"[Handler] Router tokens unavailable — retrying")
                raise Exception("RATE_LIMIT_WAIT")

            retrieval_needed = needs_retrieval(query)
            tokens_used      = 1

            if not retrieval_needed:
                print(f"[Handler] Router: NO retrieval — direct answer")

                rag_acquired = acquire_generate_tokens(r)
                if not rag_acquired:
                    raise Exception("RATE_LIMIT_WAIT")

                answer       = direct_answer(query, history, response_style)
                tokens_used += 2

                _finish(
                    r=r, job_id=job_id, query=query,
                    answer=answer, user_id=user_id,
                    conversation_id=conversation_id,
                    voice_mode=voice_mode,
                    retrieved_chunks=[], cache_key=cache_key,
                    tokens_used=tokens_used, path="direct",
                )
                return

            print(f"[Handler] Router: YES retrieval")

        else:
            print(f"[Handler] User has documents — skipping router, "
                  f"always retrieving")

        n_docs = len(document_ids) if document_ids else (1 if document_id else 0)

        structured = _detect_structured_query(search_query)

        if structured is not None:
            q_type, q_value = structured["type"], structured["value"]
            print(f"[Handler] Structured query: type={q_type} value={q_value!r}")

            if q_type == "page":
                candidates = _get_chunks_by_page(
                    user_id,
                    q_value,
                    document_id,
                    document_ids or None,
                )
                not_found_msg = (
                    f"Page {q_value} does not appear to have any extractable "
                    f"text content in your document. It may be an image-only "
                    f"page, or the document has fewer than {q_value} pages."
                )
            else:
                candidates = _get_chunks_by_section(
                    user_id,
                    q_value,
                    document_id,
                    document_ids or None,
                )
                not_found_msg = (
                    f"No section matching '{q_value}' was found in your document."
                )

            if not candidates:
                generate_acquired = acquire_generate_tokens(r)
                if not generate_acquired:
                    raise Exception("RATE_LIMIT_WAIT")
                tokens_used += 2
                _finish(
                    r=r, job_id=job_id, query=query, answer=not_found_msg,
                    user_id=user_id, conversation_id=conversation_id,
                    voice_mode=voice_mode, retrieved_chunks=[],
                    cache_key=cache_key, tokens_used=tokens_used, path="rag",
                )
                return

            print(f"[Handler] {len(candidates)} chunks via metadata lookup")

            top_chunks = mmr_rerank(
                query_embedding=embed_query(search_query),
                chunks=candidates,
                top_k=MMR_TOP_K,
                lambda_mult=MMR_LAMBDA,
            )

            generate_acquired = acquire_generate_tokens(r)
            if not generate_acquired:
                raise Exception("RATE_LIMIT_WAIT")
            tokens_used += 2

            gen_model = _route_model(r, query, n_docs)
            if gen_model["token_used"]:
                tokens_used += 1

            answer = generate_answer(
                query=query,
                context_chunks=top_chunks,
                history=history,
                style=response_style,
                model=gen_model["model"],
                role=gen_model.get("role", "rag"),
            )
            _finish(
                r=r, job_id=job_id, query=query, answer=answer,
                user_id=user_id, conversation_id=conversation_id,
                voice_mode=voice_mode, retrieved_chunks=top_chunks,
                cache_key=cache_key, tokens_used=tokens_used, path="rag",
            )
            return

        route_executor = None
        route_future   = None
        if n_docs > 1:
            route_executor = ThreadPoolExecutor(max_workers=1)
            route_future   = route_executor.submit(_route_model, r, query, n_docs)

        print(f"[Handler] Embedding query (local model — free)")
        direct_embedding = embed_query(search_query)

        print(f"[Handler] Running hybrid search (Supabase — free)")
        if document_ids:
            results_obj = supabase.schema("rag").rpc("hybrid_search_multi_doc", {
                "query_embedding": direct_embedding,
                "query_text": search_query,
                "target_user_id": user_id,
                "doc_ids": document_ids,
                "match_count": 20,
            }).execute()
            candidates = results_obj.data or []
        else:
            candidates = execute_hybrid_search(
                user_id=user_id,
                query_embedding=direct_embedding,
                query_text=search_query,
                match_count=20,
                document_id=document_id,
            )

        print(f"[Handler] Hybrid search: {len(candidates)} candidates")

        if not candidates:
            print(f"[Handler] No candidates — direct fallback")
            if route_executor is not None:
                route_executor.shutdown(wait=False)

            rag_acquired = acquire_generate_tokens(r)
            if not rag_acquired:
                raise Exception("RATE_LIMIT_WAIT")

            answer       = direct_answer(query, history, response_style)
            tokens_used += 2
            _finish(
                r=r, job_id=job_id, query=query,
                answer=answer, user_id=user_id,
                conversation_id=conversation_id,
                voice_mode=voice_mode,
                retrieved_chunks=[], cache_key=cache_key,
                tokens_used=tokens_used, path="direct_fallback",
            )
            return

        top_rrf_score  = candidates[0].get("rrf_score", 0)
        hyde_triggered = False

        print(f"[Handler] Top RRF: {top_rrf_score:.4f} "
              f"(min_useful={MIN_USEFUL_RRF_SCORE}, "
              f"hyde_threshold={HYDE_CONFIDENCE_THRESHOLD})")

        if top_rrf_score < MIN_USEFUL_RRF_SCORE:
            print(f"[Handler] RRF {top_rrf_score:.4f} < "
                  f"MIN_USEFUL {MIN_USEFUL_RRF_SCORE} — "
                  f"document not relevant — direct fallback")
            if route_executor is not None:
                route_executor.shutdown(wait=False)

            rag_acquired = acquire_generate_tokens(r)
            if not rag_acquired:
                raise Exception("RATE_LIMIT_WAIT")

            answer       = direct_answer(query, history, response_style)
            tokens_used += 2
            _finish(
                r=r, job_id=job_id, query=query,
                answer=answer, user_id=user_id,
                conversation_id=conversation_id,
                voice_mode=voice_mode,
                retrieved_chunks=[], cache_key=cache_key,
                tokens_used=tokens_used, path="direct_fallback",
            )
            return

        hyde_eligible = n_docs <= 1
        if top_rrf_score < HYDE_CONFIDENCE_THRESHOLD and hyde_eligible:
            print(f"[Handler] Weak signal — attempting HyDE")

            hyde_acquired = acquire_hyde_token(r)

            if hyde_acquired:
                tokens_used += 1
                hyde_embedding, hyp_answer = generate_hyde_embedding(query)

                if document_ids:
                    hyde_results_obj = supabase.schema("rag").rpc("hybrid_search_multi_doc", {
                        "query_embedding": hyde_embedding,
                        "query_text": search_query,
                        "target_user_id": user_id,
                        "doc_ids": document_ids,
                        "match_count": 20,
                    }).execute()
                    hyde_candidates = hyde_results_obj.data or []
                else:
                    hyde_candidates = execute_hybrid_search(
                        user_id=user_id,
                        query_embedding=hyde_embedding,
                        query_text=search_query,
                        match_count=20,
                        document_id=document_id,
                    )

                if hyde_candidates:
                    hyde_top = hyde_candidates[0].get("rrf_score", 0)
                    print(f"[Handler] HyDE RRF: {hyde_top:.4f} "
                          f"vs direct: {top_rrf_score:.4f}")

                    if hyde_top > top_rrf_score:
                        candidates     = hyde_candidates
                        hyde_triggered = True
                        print(f"[Handler] HyDE improved retrieval")
                    else:
                        print(f"[Handler] HyDE no improvement — "
                              f"keeping direct results")
            else:
                print(f"[Handler] HyDE token unavailable — proceeding")
        else:
            if not hyde_eligible:
                print(f"[Handler] Multi-doc query — HyDE skipped to reduce latency")
            else:
                print(f"[Handler] Strong signal — HyDE skipped")

        effective_top_k = MMR_TOP_K if n_docs <= 1 else min(4 * n_docs, 12)
        print(f"[Handler] Running MMR (top_k={effective_top_k}, n_docs={n_docs})")
        top_chunks = mmr_rerank(
            query_embedding=direct_embedding,
            chunks=candidates,
            top_k=effective_top_k,
            lambda_mult=MMR_LAMBDA,
        )

        print(f"[Handler] MMR selected {len(top_chunks)} chunks "
              f"pages={[c['metadata'].get('page_number') for c in top_chunks]}")

        print(f"[Handler] Acquiring {GENERATE_COST} generation token(s)")
        generate_acquired = acquire_generate_tokens(r)

        if not generate_acquired:
            print(f"[Handler] Generation tokens unavailable — retry")
            raise Exception("RATE_LIMIT_WAIT")

        tokens_used += 2

        if route_future is not None:
            gen_model = route_future.result()
            route_executor.shutdown(wait=False)
        else:
            gen_model = _route_model(r, query, n_docs)
        if gen_model["token_used"]:
            tokens_used += 1

        print(f"[Handler] Generating RAG answer "
              f"(model={gen_model['name']}, "
              f"hyde={hyde_triggered}, "
              f"chunks={len(top_chunks)}, "
              f"history={len(history)})")

        answer = generate_answer(
            query=query,
            context_chunks=top_chunks,
            history=history,
            style=response_style,
            model=gen_model["model"],
            role=gen_model.get("role", "rag"),
        )

        _finish(
            r=r,
            job_id=job_id,
            query=query,
            answer=answer,
            user_id=user_id,
            conversation_id=conversation_id,
            voice_mode=voice_mode,
            retrieved_chunks=top_chunks,
            cache_key=cache_key,
            tokens_used=tokens_used,
            path="rag",
        )

    except Exception as e:
        if "RATE_LIMIT_WAIT" in str(e):
            raise

        print(f"[Handler] Job {job_id} failed: {e}")
        _write_result(r, job_id, {
            "status":  "error",
            "message": str(e),
        })
        raise


def _user_has_documents(user_id: str) -> bool:
    try:
        result = supabase.schema("rag").table("documents") \
            .select("id") \
            .eq("user_id", user_id) \
            .eq("status", "ready") \
            .limit(1) \
            .execute()
        return len(result.data) > 0
    except Exception as e:
        print(f"[Handler] _user_has_documents error: {e} — defaulting False")
        return False


def _finish(
    r,
    job_id:           str,
    query:            str,
    answer:           str,
    user_id:          str,
    conversation_id:  str,
    voice_mode:       bool,
    retrieved_chunks: list[dict],
    cache_key:        str,
    tokens_used:      int = 0,
    path:             str = "rag",
) -> None:
    if path == "rag" and answer.startswith("This was not found in your documents."):
        path = "rag_fallback"

    save_assistant_message(
        conversation_id=conversation_id,
        user_id=user_id,
        content=answer,
        retrieved_chunks=retrieved_chunks,
        voice_url=None,
        voice_used=False,
    )

    update_conversation_timestamp(conversation_id)

    sources = [
        {
            "chunk_id":    c.get("id"),
            "document_id": c.get("document_id"),
            "page_number": c["metadata"].get("page_number"),
            "filename":    c["metadata"].get("filename"),
            "section":     c["metadata"].get("section"),
            "snippet":     c.get("content", ""),
        }
        for c in retrieved_chunks
    ]

    r.setex(cache_key, CACHE_TTL, json.dumps({"answer": answer, "sources": sources}))
    print(f"[Handler] Answer cached (TTL={CACHE_TTL}s)")

    _write_result(r, job_id, {
        "status":                  "done",
        "answer":                  answer,
        "cached":                  False,
        "sources":                 sources,
        "voice_url":               None,
        "voice_urls":              None,
        "voice_credits_remaining": _get_voice_credits(user_id),
        "tokens_used":             tokens_used,
        "path":                    path,
    })

    print(f"[Handler] Job {job_id} done "
          f"(path={path}, tokens={tokens_used})")


def _make_cache_key(user_id: str, query: str, doc_part: str, style: str) -> str:
    h = hashlib.sha256(query.lower().strip().encode()).hexdigest()
    return f"cache:{user_id}:{doc_part}:{style}:{h}"


def _get_conversation_document_ids(conversation_id: str, user_id: str) -> list[str]:
    try:
        conv = supabase.schema("rag").table("conversations") \
            .select("id") \
            .eq("id", conversation_id) \
            .eq("user_id", user_id) \
            .single() \
            .execute()
        if not conv.data:
            return []
        result = supabase.schema("rag").table("conversation_documents") \
            .select("document_id") \
            .eq("conversation_id", conversation_id) \
            .execute()
        return [row["document_id"] for row in (result.data or [])]
    except Exception as e:
        print(f"[Handler] _get_conversation_document_ids error: {e}")
        return []


def _get_conversation_document_id(conversation_id: str, user_id: str) -> str | None:
    try:
        result = supabase.schema("rag").table("conversations") \
            .select("document_id") \
            .eq("id", conversation_id) \
            .eq("user_id", user_id) \
            .single() \
            .execute()
        if not result.data:
            return None
        return result.data.get("document_id")
    except Exception as e:
        print(f"[Handler] _get_conversation_document_id error: {e}")
        return None


def _write_result(r, job_id: str, result: dict) -> None:
    _write_result_job(r, job_id, result)
    print(f"[Handler] Job result written: status={result.get('status')}")


def _get_voice_credits(user_id: str) -> int:
    try:
        result = supabase \
            .schema("rag").table("user_profiles") \
            .select("voice_credits") \
            .eq("id", user_id) \
            .single() \
            .execute()
        return result.data.get("voice_credits", 0) if result.data else 0
    except Exception:
        return 0


_PAGE_RE = re.compile(
    r'\b(?:page|pg)\.?\s*(?:number\s*|#\s*)?(\d+)\b',
    re.IGNORECASE,
)

_SECTION_RE = re.compile(
    r'\b(?:section|chapter|part|unit|module|topic)\s+(["\']?[\w\s\-\.]{2,60}["\']?)',
    re.IGNORECASE,
)


def _detect_structured_query(query: str) -> dict | None:
    page_m = _PAGE_RE.search(query)
    if page_m:
        return {"type": "page", "value": int(page_m.group(1))}

    section_m = _SECTION_RE.search(query)
    if section_m:
        raw = section_m.group(1).strip().strip("'\"")
        if raw:
            return {"type": "section", "value": raw}

    return None


def _get_chunks_by_page(
    user_id:     str,
    page_number: int,
    document_id: str | None,
    document_ids: list[str] | None = None,
) -> list[dict]:
    params: dict = {
        "target_user_id": user_id,
        "target_page":    page_number,
        "match_count":    20,
    }
    if document_ids:
        params["target_doc_ids"] = document_ids
    else:
        params["target_doc_id"] = document_id
    result = supabase.schema("rag").rpc("get_chunks_by_page", params).execute()
    return result.data or []


def _get_chunks_by_section(
    user_id:         str,
    heading_pattern: str,
    document_id:     str | None,
    document_ids:    list[str] | None = None,
) -> list[dict]:
    params: dict = {
        "target_user_id":  user_id,
        "heading_pattern": heading_pattern,
        "match_count":     20,
    }
    if document_ids:
        params["target_doc_ids"] = document_ids
    else:
        params["target_doc_id"] = document_id
    result = supabase.schema("rag").rpc("get_chunks_by_section", params).execute()
    return result.data or []


def _route_model(r, query: str, n_docs: int) -> dict:
    if n_docs <= 1:
        return {"model": _llm_model("rag"), "name": "rag", "role": "rag", "token_used": False}

    if not acquire_router_token(r):
        print(f"[Handler] Router token unavailable — heuristic fallback → multi")
        return {"model": _llm_model("multi"), "name": "multi", "role": "multi", "token_used": False}

    role  = route_generation_model(query, n_docs)
    model = _llm_model(role)
    return {"model": model, "name": role, "role": role, "token_used": True}
