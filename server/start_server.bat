@echo off
setlocal
cd /d "%~dp0"

if not exist .env (
  echo missing server/.env
  exit /b 1
)
if not exist storage mkdir storage
if not exist venv\Scripts\uvicorn.exe (
  venv\Scripts\pip install -r requirements.lock
  if errorlevel 1 exit /b 1
)

if "%PORT%"=="" set PORT=8000
venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port %PORT%
