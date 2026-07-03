#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "============================================"
echo " Ontario EV Betting Scanner"
echo "============================================"

if [ ! -d "backend/venv" ]; then
  python3 -m venv backend/venv
fi

source backend/venv/bin/activate
pip install -q -r backend/requirements.txt

if [ ! -d "frontend/dist" ]; then
  echo "Building frontend..."
  cd frontend && npm install && npm run build && cd ..
fi

echo ""
echo "Starting server at http://localhost:8000"
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
