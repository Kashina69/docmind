# Client setup

Next.js + Supabase auth. Talks to server on `NEXT_PUBLIC_API_URL`.

## 1. Env (`.env`)
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_...
NEXT_PUBLIC_API_URL=http://localhost:8000
```
Must point at same Supabase project as `server/.env`.

## 2. Install
```bash
npm install
```

## 3. Run
```bash
npm run dev              # → http://localhost:3000
```
Or from repo root: `./start_project.sh` / `start_project.bat` (boots server + client, waits for `localhost:8000` health first).
