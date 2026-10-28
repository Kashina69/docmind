# Server setup

Python `3.11` only. Lockfile was built on cp311 wheels.

## 1. DB
```bash
supabase link --project-ref <ref>
supabase db push
```
Migrations live in `supabase/migrations/`. Must be timestamp-prefixed or push ignores them.

## 2. Env (`.env`)
```
SUPABASE_URL=
SUPABASE_SERVICE_KEY=sb_secret_...     # service_role, ingestion bypasses RLS
SUPABASE_ANON_KEY=sb_publishable_...
LLM_API_URL=https://api.deepseek.com
LLM_API_KEY=
MODEL_RAG=deepseek-chat
MODEL_MULTI=deepseek-chat
MODEL_HYDE=deepseek-chat
MODEL_ROUTER=deepseek-chat
MODEL_REWRITE=deepseek-chat
MODEL_SUMMARIZER=deepseek-chat
# optional per-role thinking: disabled/low/medium/high/max, blank = provider default
# THINKING_DEFAULT=low
# THINKING_RAG=low etc (RAG/MULTI/ROUTER/REWRITE/HYDE/SUMMARIZER)
APP_BASE_URL=http://localhost:8000
STORAGE_DIR=storage
```
Must point at same Supabase project as `client/.env`.

## 3. Install
```bash
python3.11 -m venv venv
./venv/bin/pip install -r requirements.lock
```
`requirements.txt` = direct deps. `requirements.lock` = frozen working set. After adding a dep: install, verify, re-freeze:
```bash
./venv/bin/pip freeze | grep -v -E "^(pip|setuptools|wheel)==" | sort > requirements.lock
```
Windows: use `py -3.11 -m venv venv` then `venv\Scripts\pip install -r requirements.lock`.

## 4. Run
```bash
./start_server.sh            # Linux/macOS
start_server.bat             # Windows cmd
```
Or both server + client from repo root: `./start_project.sh` / `start_project.bat`.

Verify: `curl localhost:8000/` → `{"status":"ok"}`. First run downloads `BAAI/bge-large-en-v1.5` (~1GB) and creates `storage/`.
