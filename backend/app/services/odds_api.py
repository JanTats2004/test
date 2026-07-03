"""
Ingest The Odds API responses into the local SQLite database.

Uses odds_api_client (licensed provider). Does not scrape sportsbook sites.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Event, Odds
from app.services.normalizer import (
    build_event_id,
    normalize_selection,
    normalize_sportsbook,
    normalize_team,
)
from app.services.odds_api_client import (
    OddsAPIClient,
    OddsAPIError,
    get_client,
)
from app.services.odds_utils import american_to_decimal

# Map known API bookmaker keys to Ontario display names when available
BOOKMAKER_MAP = {
    "fanduel": "FanDuel Ontario",
    "draftkings": "DraftKings Ontario",
    "betmgm": "BetMGM Ontario",
    "williamhill_us": "Caesars Ontario",
    "bet365": "Bet365 Ontario",
    "bet365_us": "Bet365 Ontario",
    "espnbet": "theScore Bet",
}


def is_configured() -> bool:
    return get_client().is_configured


def fetch_sports(all_sports: bool = False) -> list[dict]:
    return get_client().fetch_sports(all_sports=all_sports)


def fetch_odds(
    sport_key: str,
    regions: str | list[str] = "us",
    markets: str | list[str] = ("moneyline", "spread", "totals"),
) -> dict:
    return get_client().fetch_odds(
        sport_key=sport_key,
        regions=regions,
        markets=markets,
        odds_format="american",
    )


def _resolve_sportsbook(book_key: str, book_title: str) -> str:
    mapped = BOOKMAKER_MAP.get(book_key)
    if mapped:
        return mapped
    return normalize_sportsbook(book_title) if book_title else book_key


def ingest_api_odds(db: Session, api_data: list[dict]) -> dict[str, int]:
    """Parse The Odds API event list and upsert into database."""
    events_created = 0
    odds_created = 0
    odds_updated = 0
    now = datetime.utcnow()

    for event_data in api_data:
        sport = event_data.get("sport_title", event_data.get("sport_key", "unknown"))
        league = event_data.get("sport_title", sport)
        commence = datetime.fromisoformat(event_data["commence_time"].replace("Z", "+00:00"))
        home_team = event_data["home_team"]
        away_team = event_data["away_team"]
        event_id = build_event_id(sport, league, commence.isoformat(), home_team, away_team)

        existing_event = db.query(Event).filter(Event.event_id == event_id).first()
        if not existing_event:
            db.add(
                Event(
                    event_id=event_id,
                    sport=sport,
                    league=league,
                    start_time=commence.replace(tzinfo=None),
                    home_team=home_team,
                    away_team=away_team,
                    home_team_normalized=normalize_team(home_team),
                    away_team_normalized=normalize_team(away_team),
                )
            )
            events_created += 1

        for bookmaker in event_data.get("bookmakers", []):
            book_key = bookmaker.get("key", "")
            book_title = bookmaker.get("title", book_key)
            sportsbook = _resolve_sportsbook(book_key, book_title)

            for market_data in bookmaker.get("markets", []):
                market_key = market_data.get("key", "")
                from app.services.odds_api_client import API_TO_MARKET

                market = API_TO_MARKET.get(market_key)
                if not market:
                    continue

                for outcome in market_data.get("outcomes", []):
                    name = outcome["name"]
                    price = int(outcome["price"])
                    point = outcome.get("point")
                    line = float(point) if point is not None else None

                    selection_norm = normalize_selection(name, market, home_team, away_team)
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
                        existing.selection = name
                        existing.american_odds = price
                        existing.decimal_odds = decimal_odds
                        existing.timestamp = now
                        odds_updated += 1
                    else:
                        db.add(
                            Odds(
                                event_id=event_id,
                                sportsbook=sportsbook,
                                market=market,
                                selection=name,
                                selection_normalized=selection_norm,
                                line=line,
                                american_odds=price,
                                decimal_odds=decimal_odds,
                                timestamp=now,
                            )
                        )
                        odds_created += 1

    db.commit()
    return {
        "events_created": events_created,
        "odds_created": odds_created,
        "odds_updated": odds_updated,
    }


__all__ = [
    "OddsAPIError",
    "fetch_sports",
    "fetch_odds",
    "ingest_api_odds",
    "is_configured",
]
