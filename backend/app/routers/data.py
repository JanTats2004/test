from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import MARKETS, ONTARIO_SPORTSBOOKS, Event, Odds
from app.schemas import AppSettingsOut, EventOut, OddsOut
from app.schemas_odds_api import OddsAPIFetchRequest, OddsAPIFetchResponse
from app.services.odds_api import OddsAPIError, fetch_odds, fetch_sports, ingest_api_odds, is_configured
from app.services.odds_api_client import SUPPORTED_REGIONS

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
        odds_api_regions=list(SUPPORTED_REGIONS),
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


# Stage 2: The Odds API endpoints
@router.get("/odds-api/sports")
def odds_api_sports(all_sports: bool = Query(default=False)):
    if not is_configured():
        raise HTTPException(status_code=400, detail="ODDS_API_KEY not configured. Set it in backend/.env")
    try:
        sports = fetch_sports(all_sports=all_sports)
        return [
            {
                "key": s.get("key"),
                "title": s.get("title"),
                "group": s.get("group"),
                "active": s.get("active"),
            }
            for s in sports
        ]
    except OddsAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/odds-api/regions")
def odds_api_regions():
    return {"regions": list(SUPPORTED_REGIONS)}


@router.post("/odds-api/fetch", response_model=OddsAPIFetchResponse)
def odds_api_fetch(request: OddsAPIFetchRequest, db: Session = Depends(get_db)):
    """Fetch odds from The Odds API, store in DB, and return summary."""
    if not is_configured():
        raise HTTPException(status_code=400, detail="ODDS_API_KEY not configured. Set it in backend/.env")
    try:
        result = fetch_odds(
            sport_key=request.sport_key,
            regions=request.regions,
            markets=request.markets,
        )
        ingest_result = ingest_api_odds(db, result["events"])
        return OddsAPIFetchResponse(
            sport_key=result["sport_key"],
            regions=result["regions"],
            markets=result["markets"],
            event_count=result["event_count"],
            row_count=result["row_count"],
            events_created=ingest_result["events_created"],
            odds_created=ingest_result["odds_created"],
            odds_updated=ingest_result["odds_updated"],
            fetched_at=result["fetched_at"],
            requests_remaining=result.get("requests_remaining"),
        )
    except OddsAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/odds-api/refresh/{sport_key}")
def odds_api_refresh(
    sport_key: str,
    regions: str = Query(default="us"),
    markets: str = Query(default="moneyline,spread,totals"),
    db: Session = Depends(get_db),
):
    """Pull odds from The Odds API for a given sport (legacy endpoint)."""
    if not is_configured():
        raise HTTPException(status_code=400, detail="ODDS_API_KEY not configured. Set it in backend/.env")
    try:
        result = fetch_odds(sport_key, regions=regions, markets=markets)
        ingest_result = ingest_api_odds(db, result["events"])
        return {
            "sport_key": sport_key,
            **ingest_result,
            "events_in_response": result["event_count"],
            "fetched_at": result["fetched_at"],
        }
    except OddsAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/odds-api/preview")
def odds_api_preview(
    sport_key: str = Query(...),
    regions: str = Query(default="us"),
    markets: str = Query(default="moneyline,spread,totals"),
):
    """Fetch odds from API and return flat rows without saving (for preview tables)."""
    if not is_configured():
        raise HTTPException(status_code=400, detail="ODDS_API_KEY not configured. Set it in backend/.env")
    try:
        result = fetch_odds(sport_key, regions=regions, markets=markets)
        return {
            "sport_key": sport_key,
            "regions": result["regions"],
            "markets": result["markets"],
            "fetched_at": result["fetched_at"],
            "requests_remaining": result.get("requests_remaining"),
            "rows": result["rows"],
        }
    except OddsAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
