@echo off
REM Ontario EV Betting Scanner - Windows Launcher
REM Requires Python 3.11+ and Node.js 18+

echo ============================================
echo  Ontario EV Betting Scanner
echo ============================================
echo.

cd /d "%~dp0.."

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Install Python 3.11+ from https://python.org
    pause
    exit /b 1
)

REM Setup backend venv if needed
if not exist "backend\venv" (
    echo Creating Python virtual environment...
    python -m venv backend\venv
)

call backend\venv\Scripts\activate.bat
pip install -q -r backend\requirements.txt
pip install -q pytest

REM Create backend\.env from template if missing
if not exist "backend\.env" (
    if exist "backend\.env.example" (
        copy backend\.env.example backend\.env >nul
        echo Created backend\.env from .env.example
    )
)

REM Build frontend (ensures localhost:8000 has latest Odds API UI)
if exist "frontend\package.json" (
    echo Building frontend...
    cd frontend
    call npm install --silent 2>nul
    call npm run build
    cd ..
)

echo.
cd backend
python -c "from app.config import settings; ok=bool(settings.odds_api_key and settings.odds_api_key!='your_api_key_here'); print('Odds API key:', 'CONFIGURED' if ok else 'NOT SET - edit backend\\.env')" 2>nul
echo.
echo Starting server at http://localhost:8000
echo After adding/changing .env, restart this script (Ctrl+C then run again).
echo Press Ctrl+C to stop.
echo.

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
