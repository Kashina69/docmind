@echo off
setlocal
set ROOT=%~dp0
if "%ROOT:~-1%"=="\" set ROOT=%ROOT:~0,-1%

if not exist "%ROOT%\server\.env" (
  echo missing server/.env
  exit /b 1
)
if not exist "%ROOT%\client\.env" (
  echo missing client/.env
  exit /b 1
)

if not exist "%ROOT%\server\venv" (
  py -3.11 -m venv "%ROOT%\server\venv"
  if errorlevel 1 exit /b 1
)
if not exist "%ROOT%\server\venv\Scripts\uvicorn.exe" (
  "%ROOT%\server\venv\Scripts\pip" install -r "%ROOT%\server\requirements.lock"
  if errorlevel 1 exit /b 1
)
if not exist "%ROOT%\client\node_modules" (
  pushd "%ROOT%\client"
  call npm install
  if errorlevel 1 exit /b 1
  popd
)

start "docmind-server" /min cmd /c ""%ROOT%\server\start_server.bat""

set /a TRIES=30
:waitloop
curl -sf http://localhost:8000/ >nul 2>&1
if not errorlevel 1 goto :ready
timeout /t 1 /nobreak >nul
set /a TRIES-=1
if %TRIES% gtr 0 goto :waitloop
echo server did not start in time
exit /b 1

:ready
cd /d "%ROOT%\client"
call npm run dev
