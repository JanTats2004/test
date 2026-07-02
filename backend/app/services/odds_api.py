"""
Stage 2: Odds API integration via The Odds API (licensed provider).

Requires ODDS_API_KEY environment variable. Does not scrape sportsbook sites.
https://the-odds-api.com/
"""

from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Event, Odds
from app.services.normalizer import (
    build_event_id,
    normalize_market,
    normalize_selection,
    normalize_sportsbook,
    normalize_team,
)
from app.services.odds_utils import american_to_decimal, decimal_to_american

# Map The Odds API bookmaker keys to Ontario display names
BOOKMAKER_MAP = {
    "fanduel": "FanDuel Ontario",
    "draftkings": "DraftKings Ontario",
    "betmgm": "BetMGM Ontario",
    "williamhill_us": "Caesars Ontario",
    "bet365": "Bet365 Ontario",
}

MARKET_MAP = {
    "h2h": "moneyline",
    "spreads": "spread",
    "totals": "totals",
}

ONTARIO_REGION = "us"  # The Odds API uses region codes; Ontario books often under us/ca


class OddsAPIError(Exception):
    pass


def is_configured() -> bool:
    return bool(settings.odds_api_key)


async def fetch_sports() -> list[dict]:
    if not is_configured():
        raise OddsAPIError("ODDS_API_KEY is not configured")

    url = f"{settings.odds_api_base_url}/sports"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params={"apiKey": settings.odds_api_key})
        response.raise_for_status()
        return response.json()


async def fetch_odds(sport_key: str, markets: str = "h2h,spreads,totals") -> list[dict]:
    if not is_configured():
        raise OddsAPIError("ODDS_API_KEY is not configured")

    url = f"{settings.odds_api_base_url}/sports/{sport_key}/odds"
    params = {
        "apiKey": settings.odds_api_key,
        "regions": "us",
        "markets": markets,
        "oddsFormat": "american",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def _parse_api_event(event_data: dict) -> tuple[str, Event]:
    sport = event_data.get("sport_title", event_data.get("sport_key", "unknown"))
    league = event_data.get("sport_title", sport)
    commence = datetime.fromisoformat(event_data["commence_time"].replace("Z", "+00:00"))
    home_team = event_data["home_team"]
    away_team = event_data["away_team"]
    event_id = build_event_id(sport, league, commence.isoformat(), home_team, away_team)

    return event_id, Event(
        event_id=event_id,
        sport=sport,
        league=league,
        start_time=commence.replace(tzinfo=None),
        home_team=home_team,
        away_team=away_team,
        home_team_normalized=normalize_team(home_team),
        away_team_normalized=normalize_team(away_team),
    )


def ingest_api_odds(db: Session, api_data: list[dict]) -> dict[str, int]:
    """Parse The Odds API response and upsert into database."""
    events_created = 0
    odds_created = 0
    now = datetime.utcnow()

    for event_data in api_data:
        event_id, event = _parse_api_event(event_data)
        existing_event = db.query(Event).filter(Event.event_id == event_id).first()
        if not existing_event:
            db.add(event)
            events_created += 1

        home_team = event_data["home_team"]
        away_team = event_data["away_team"]

        for bookmaker in event_data.get("bookmakers", []):
            book_key = bookmaker.get("key", "")
            sportsbook = BOOKMAKER_MAP.get(book_key)
            if not sportsbook:
                continue

            for market_data in bookmaker.get("markets", []):
                market_key = market_data.get("key", "")
                market = MARKET_MAP.get(market_key)
                if not market:
                    continue

                for outcome in market_data.get("outcomes", []):
                    name = outcome["name"]
                    price = int(outcome["price"])
                    point = outcome.get("point")
                    line = float(point) if point is not None else None

                    if market == "totals":
                        selection = name
                    elif market == "spread":
                        selection = name
                    else:
                        selection = name

                    selection_norm = normalize_selection(selection, market, home_team, away_team)
                    decimal_odds = american_to_decimal(price)

                    existing = (
                        db.query(Odds)
                        .filter(
                            Odds.event_id == event_id,
                            Odds.sportsbook == sportsbook,
                            Odds.market == market,
                            Odds.selection_normalized == selection_norm,
                            Odds.line == line,
                        )
                        .first()
                    )

                    if existing:
                        existing.american_odds = price
                        existing.decimal_odds = decimal_odds
                        existing.timestamp = now
                    else:
                        db.add(
                            Odds(
                                event_id=event_id,
                                sportsbook=sportsbook,
                                market=market,
                                selection=selection,
                                selection_normalized=selection_norm,
                                line=line,
                                american_odds=price,
                                decimal_odds=decimal_odds,
                                timestamp=now,
                            )
                        )
                        odds_created += 1

    db.commit()
    return {"events_created": events_created, "odds_created": odds_created}
