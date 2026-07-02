# Ontario EV Betting Scanner - Windows PowerShell Launcher
# Requires Python 3.11+ and Node.js 18+

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "============================================"
Write-Host " Ontario EV Betting Scanner"
Write-Host "============================================"
Write-Host ""

# Python venv
if (-not (Test-Path "backend\venv")) {
    Write-Host "Creating Python virtual environment..."
    python -m venv backend\venv
}

& "backend\venv\Scripts\Activate.ps1"
pip install -q -r backend\requirements.txt

# Frontend build
if (-not (Test-Path "frontend\dist")) {
    Write-Host "Building frontend..."
    Set-Location frontend
    npm install
    npm run build
    Set-Location $Root
}

Write-Host ""
Write-Host "Starting server at http://localhost:8000"
Write-Host "Press Ctrl+C to stop."
Write-Host ""

Set-Location backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
