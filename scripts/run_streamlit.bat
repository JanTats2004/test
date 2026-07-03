@echo off
REM Ontario EV Scanner — Streamlit UI (Python only, no Node.js build needed)

cd /d "%~dp0.."

if not exist "backend\venv" (
    python -m venv backend\venv
)

call backend\venv\Scripts\activate.bat
pip install -q -r backend\requirements.txt

if not exist "backend\.env" (
    if exist "backend\.env.example" (
        copy backend\.env.example backend\.env >nul
        echo Created backend\.env — add your ODDS_API_KEY before fetching odds.
    )
)

echo.
echo Starting Streamlit at http://localhost:8501
echo Press Ctrl+C to stop.
echo.

cd backend
streamlit run app.py --server.port 8501
