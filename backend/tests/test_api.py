import io
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

SAMPLE_CSV = """sport,league,start_time,home_team,away_team,sportsbook,market,selection,line,american_odds
NBA,NBA,2026-07-03T19:30:00,Toronto Raptors,Boston Celtics,theScore Bet,moneyline,Toronto Raptors,,+105
NBA,NBA,2026-07-03T19:30:00,Toronto Raptors,Boston Celtics,theScore Bet,moneyline,Boston Celtics,,-125
NBA,NBA,2026-07-03T19:30:00,Toronto Raptors,Boston Celtics,FanDuel Ontario,moneyline,Toronto Raptors,,+120
NBA,NBA,2026-07-03T19:30:00,Toronto Raptors,Boston Celtics,FanDuel Ontario,moneyline,Boston Celtics,,-140
NBA,NBA,2026-07-03T19:30:00,Toronto Raptors,Boston Celtics,DraftKings Ontario,moneyline,Toronto Raptors,,+108
NBA,NBA,2026-07-03T19:30:00,Toronto Raptors,Boston Celtics,DraftKings Ontario,moneyline,Boston Celtics,,-128
"""


@pytest.fixture()
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    os.unlink(path)


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_csv_import_and_scan(client):
    files = {"file": ("odds.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")}
    res = client.post("/api/import/csv", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["odds_created"] == 6

    res = client.get("/api/ev/scan", params={"min_ev": 0.0})
    assert res.status_code == 200
    scan = res.json()
    assert scan["total_opportunities"] >= 1


def test_export_csv(client):
    files = {"file": ("odds.csv", io.BytesIO(SAMPLE_CSV.encode()), "text/csv")}
    client.post("/api/import/csv", files=files)
    res = client.get("/api/ev/export", params={"min_ev": 0.0})
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "ev_percent" in res.text.split("\n")[0]
