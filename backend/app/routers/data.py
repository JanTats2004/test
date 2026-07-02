from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import MARKETS, ONTARIO_SPORTSBOOKS, Event, Odds
from app.schemas import AppSettingsOut, EventOut, OddsOut
from app.services.odds_api import OddsAPIError, fetch_odds, fetch_sports, ingest_api_odds, is_configured

router = APIRouter(prefix="/api", tags=["data"])


@router.get("/settings", response_model=AppSettingsOut)
def get_settings():
    return AppSettingsOut(
        sportsbooks=ONTARIO_SPORTSBOOKS,
        markets=MARKETS,
        stale_odds_minutes=settings.stale_odds_minutes,
        default_ev_threshold=settings.default_ev_threshold,
        default_bankroll=settings.default_bankroll,
        default_flat_stake=settings.default_flat_stake,
        default_kelly_fraction=settings.default_kelly_fraction,
        odds_api_configured=is_configured(),
    )


@router.get("/events", response_model=list[EventOut])
def list_events(sport: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Event)
    if sport:
        query = query.filter(Event.sport == sport)
    return query.order_by(Event.start_time).all()


@router.get("/odds", response_model=list[OddsOut])
def list_odds(
    event_id: str | None = None,
    sportsbook: str | None = None,
    market: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Odds)
    if event_id:
        query = query.filter(Odds.event_id == event_id)
    if sportsbook:
        query = query.filter(Odds.sportsbook == sportsbook)
    if market:
        query = query.filter(Odds.market == market)
    return query.order_by(Odds.timestamp.desc()).all()


@router.delete("/odds")
def clear_odds(db: Session = Depends(get_db)):
    count = db.query(Odds).delete()
    db.commit()
    return {"deleted": count}


@router.delete("/events")
def clear_events(db: Session = Depends(get_db)):
    count = db.query(Event).delete()
    db.commit()
    return {"deleted": count}


# Stage 2: Odds API endpoints
@router.get("/odds-api/sports")
async def odds_api_sports():
    if not is_configured():
        raise HTTPException(status_code=400, detail="ODDS_API_KEY not configured. Set it in .env file.")
    try:
        return await fetch_sports()
    except OddsAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/odds-api/refresh/{sport_key}")
async def odds_api_refresh(sport_key: str, db: Session = Depends(get_db)):
    """Stage 2/3: Pull odds from The Odds API for a given sport."""
    if not is_configured():
        raise HTTPException(status_code=400, detail="ODDS_API_KEY not configured. Set it in .env file.")
    try:
        data = await fetch_odds(sport_key)
        result = ingest_api_odds(db, data)
        return {"sport_key": sport_key, **result, "events_in_response": len(data)}
    except OddsAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
