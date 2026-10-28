# Divergence: clone/server vs original lambdas

How the FastAPI monolith in `clone/server/app/` differs from the
serverless original in `original/lambdas/`, after the refactor that
mirrors the original's lambda boundaries as packages.

## Layout map (refactored clone → original)

| Clone package | Original lambda | Match |
|---|---|---|
| `app/routes/` (health, uploads, query, generate, library + `deps.py`) | `submit/handler.py` + `poll/handler.py` | ✅ Same handler-per-endpoint split; `deps.py` holds the shared auth/supabase/cache-key helpers that `submit` inlines |
| `app/pipelines/ingestion/` (pipeline, extractor, chunker, structure_detector, embedder) | `ingestion_lambda/` (handler, extractor, chunker, structure_detector, embedder, embed_worker) | ✅ 1:1 module match (see §1) |
| `app/pipelines/generation/` (summarize, flashcards, fetch) | `generation_lambda/tasks/` (summarize, flashcards, utils) | ✅ 1:1 task split; `fetch.py` groups the Supabase reads (see §2) |
| `app/pipelines/query/` (pipeline, retrieval, structured, models, finish, history, hyde, mmr, classifier) | `query_lambda/` (handler, history, hyde, mmr, classifier, sarvam, nvidia) | ✅ Orchestrator + same helper split (see §3) |
| `app/llm/` (client, router, answers, prompts) | `query_lambda/sarvam.py` + `nvidia.py`, `shared_lambda/summarizer_llm.py` | ⚠️ Collapsed into one provider (see §4) |
| `app/shared/` (auth, supabase_client, rate_limiter, secrets, utils, jobs, storage, store) | `shared_lambda/` (auth, supabase_client, rate_limiter, secrets, utils, summarizer_llm, classifier, version_check) | ✅ Same cross-cutting role (see §5) |
| `app/startup.py` (lifespan recovery) | SQS redelivery (implicit) | ⚠️ No queue in the monolith, so stuck-job recovery is explicit (see §6) |

## 1. Ingestion: same modules, sync instead of queued

- Original splits work across SQS stages: `handler.py` stores chunks with
  `embedding=NULL`, enqueues per-window messages (`_build_windows`,
  `_store_window`, `_enqueue_window`, `_send_embed_message`), and
  `embed_worker.py` embeds then `_finalize_document`.
- Clone `pipelines/ingestion/pipeline.py` does extract → chunk → dedupe →
  store → embed → mark-ready inline in one function. The stage helpers have
  no equivalent because there is no queue; `EMBED_BATCH_SIZE = 32` loops
  replace the window messages.
- Consequence: a crash mid-ingest leaves `processing` rows, which
  `startup.py` re-ingests on boot (see §6).

## 2. Generation: same task split, shared fetch layer added

- Original `summarize.py` / `flashcards.py` call the supabase client inline
  for whatever rows they need; no shared fetch module exists.
- Clone adds `pipelines/generation/fetch.py` (formerly `sources.py`) with
  `fetch_source_content` / `fetch_conversation_transcript` /
  `fetch_document_chunks` so both tasks share one fetch path. Purely
  additive — task entry signatures are unchanged.

## 3. Query: same pipeline steps, helpers factored out of the orchestrator

- Original `query_lambda/handler.py` (~850 lines) keeps retrieval helpers
  (`_get_chunks_by_page`, `_get_chunks_by_section`, `_get_conversation_*`,
  `_user_has_documents`, `_route_model`, `_finish`, `_write_result`,
  `_detect_structured_query`) inside the handler file.
- Clone `pipelines/query/pipeline.py` keeps only `run_query_pipeline` and
  imports the rest from `retrieval.py`, `structured.py`, `models.py`,
  `finish.py`. Step order, token accounting, and threshold constants
  (`HYDE_CONFIDENCE_THRESHOLD = 0.02`, `MIN_USEFUL_RRF_SCORE = 0.005`,
  `MMR_TOP_K = 5`, `MMR_LAMBDA = 0.7`) are unchanged.

## 4. LLM layer: two providers collapsed into one OpenAI-compatible client

- Original calls Sarvam (`sarvam.py`: HyDE, answers, TTS, routing) and
  Nvidia (`nvidia.py`) directly, plus `summarizer_llm.py` for generation
  tasks.
- Clone routes everything through `llm/client.py` (`LLM_API_URL` /
  `LLM_API_KEY` + per-role `MODEL_*` overrides): `router.py` (rewrite /
  needs_retrieval / route_generation_model), `answers.py`
  (generate_answer / direct_answer), `prompts.py` (build/format/strip).
- Voice/TTS (`_handle_voice`, `_split_tts_chunks`, voice credits in job
  results) is stubbed out in the clone: `voice_url`/`voice_urls` are always
  `None`, `voice_credits_remaining` still reported. Re-adding TTS means
  porting `submit` + `query_lambda` voice paths onto the new client.

## 5. Shared: same role, local stand-ins for AWS services

- `auth`, `supabase_client`, `rate_limiter`, `secrets`, `utils` mirror
  `shared_lambda` 1:1 by name and responsibility.
- `shared/jobs.py` = `generation_lambda/tasks/utils.py` (`write_result` /
  `read_result` with `job:` keys, TTL 3600).
- `shared/rate_limiter.py` + `shared/store.py`: the original uses Upstash
  Redis REST; the clone uses an in-memory `SimpleStore` with the same
  `get/setex/zadd/zcard/zremrangebyscore` surface, so rate-limit behavior
  matches but does not persist across restarts.
- `shared/storage.py`: local-filesystem stand-in for S3 (`put_file` /
  `delete_file` / `serve_url` → `/files/{key}`).
- `shared/secrets.py`: reads `.env` instead of AWS Secrets Manager.
- No equivalent of `version_check.py` (Lambda layer pin check — N/A in a
  monolith).

## 6. Async model: BackgroundTasks + lifespan instead of SQS + Lambdas

- Original: API Gateway (29s timeout) → SQS → Lambda; `RATE_LIMIT_WAIT`
  re-raises so the message returns to the queue; `poll` Lambda reads
  `job:{job_id}` from Redis.
- Clone: FastAPI `BackgroundTasks` run `run_query_pipeline` /
  `_run_generation_with_retry` in-process with one 10s retry, then write
  `{"status": "error"}` to the job key. Same `job:` key format and same
  `GET /result/{job_id}` polling contract.
- Because there is no queue redelivery, `startup.py` re-ingests documents
  stuck in `processing`/`indexing` on boot — the monolith equivalent of
  SQS visibility-timeout redrive.
