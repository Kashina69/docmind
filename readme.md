# DocMind

RAG over your PDFs: upload, ask, get answers with sources. Next.js client + FastAPI server + Supabase (auth, Postgres + pgvector).

## Quick start
```bash
# 1. DB (from server/)
supabase link --project-ref <ref>
supabase db push

# 2. env — fill in server/.env and client/.env (see setup guides below)

# 3. run everything
./start_project.sh            # Linux/macOS, from repo root
start_project.bat             # Windows cmd, from repo root
```
Opens client on `localhost:3000`, server on `localhost:8000`.

## Setup guides
- Backend: `server/setup.md` (Python 3.11, DB, env, install, run)
- Frontend: `client/setup.md` (env, install, run)

Both `.env` files must point at the SAME Supabase project.

## Layout
- `server/` — FastAPI (`app/`), Supabase migrations (`supabase/migrations/`). Overview: `server/readme.md`.
- `client/` — Next.js. Overview: `client/readme.md`.

## Test
Sign up in UI → upload PDF → ask question. Queries are async, frontend polls `GET /result/{job_id}`.
