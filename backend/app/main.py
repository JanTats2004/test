from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers import data, ev, import_csv

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Ontario EV Betting Scanner",
    description="Compare odds across Ontario sportsbooks and identify positive EV bets.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(import_csv.router)
app.include_router(ev.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "stage": 1, "features": ["csv_upload", "ev_scan", "csv_export"]}


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
