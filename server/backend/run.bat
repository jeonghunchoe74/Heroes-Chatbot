@echo off
cd /d "%~dp0"

echo [1] Loading .env ...
if exist .env (
    for /f "tokens=1,2 delims==" %%a in ('type .env ^| findstr /v "#"') do set %%a=%%b
)

if "%HOST%"=="" set HOST=127.0.0.1
if "%PORT%"=="" set PORT=8000

REM ✅ PYTHONPATH를 backend 루트로 지정
set PYTHONPATH=%CD%

start http://%HOST%:%PORT%/docs
REM 우선 reload 없이 테스트, 문제 해결되면 --reload 복구
uvicorn app.main:app --host %HOST% --port %PORT%
