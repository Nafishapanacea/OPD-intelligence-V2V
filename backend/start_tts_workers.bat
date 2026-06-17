@echo off
REM Start TTS Worker Pool for OPD Intelligence
REM This script starts 5 dedicated TTS worker processes
REM Each worker handles concurrent OmniVoice inference with semaphore limiting

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ==========================================
echo OPD Intelligence V2V - TTS Worker Pool
echo ==========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found
    echo Run: python -m venv venv
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if Redis is running
echo Checking Redis connection...
python -c "import redis; r = redis.Redis(host='localhost', port=6379); r.ping()" >nul 2>&1
if errorlevel 1 (
    echo WARNING: Redis not found on localhost:6379
    echo Make sure Redis is running: redis-server
)

echo.
echo Starting 4 Optimized TTS Workers...
echo.

REM Start workers in separate command windows
for /L %%i in (1,1,4) do (
    echo [TTS Worker %%i] Starting with MAX_CONCURRENT=2...
    start "TTS-Worker-%%i" cmd /c "set WORKER_ID=%%i&& set MAX_CONCURRENT=2&& python -m app.workers.tts_worker"
)

echo.
echo ✅ All 4 TTS workers started in background windows
echo.
echo To monitor workers:
echo   - Each window shows worker logs in real-time
echo   - Workers pull tasks from Redis queue: "tts_tasks"
echo   - Results stored in Redis with key: "tts_result:{task_id}"
echo.
echo To stop workers:
echo   - Close the individual worker windows, or
echo   - Run: taskkill /F /IM python.exe /T
echo.
echo To check queue status:
echo   - redis-cli LLEN tts_tasks
echo   - redis-cli DBSIZE
echo.

pause
