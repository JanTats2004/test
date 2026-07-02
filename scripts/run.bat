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

REM Build frontend if needed
if not exist "frontend\dist" (
    echo Building frontend...
    cd frontend
    call npm install
    call npm run build
    cd ..
)

echo.
echo Starting server at http://localhost:8000
echo Press Ctrl+C to stop.
echo.

cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
