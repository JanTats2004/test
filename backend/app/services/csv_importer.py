import csv
import io
from datetime import datetime

from dateutil import parser as date_parser
from sqlalchemy.orm import Session

from app.models import Event, Odds
from app.schemas import CSVImportResult
from app.services.normalizer import (
    build_event_id,
    normalize_market,
    normalize_selection,
    normalize_sportsbook,
    normalize_team,
)
from app.services.odds_utils import american_to_decimal

REQUIRED_COLUMNS = {
    "sport",
    "league",
    "start_time",
    "home_team",
    "away_team",
    "sportsbook",
    "market",
    "selection",
    "american_odds",
}

OPTIONAL_COLUMNS = {"line", "decimal_odds", "event_id"}


def _parse_american(value: str) -> int:
    cleaned = value.strip().replace("+", "")
    return int(cleaned)


def _parse_line(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def _parse_timestamp(value: str | None) -> datetime:
    if not value or str(value).strip() == "":
        return datetime.utcnow()
    return date_parser.parse(value)


def import_odds_csv(db: Session, file_content: str) -> CSVImportResult:
    reader = csv.DictReader(io.StringIO(file_content))
    if not reader.fieldnames:
        return CSVImportResult(
            events_created=0,
            events_updated=0,
            odds_created=0,
            odds_updated=0,
            errors=["CSV file is empty or missing headers"],
        )

    headers = {h.strip().lower() for h in reader.fieldnames}
    missing = REQUIRED_COLUMNS - headers
    if missing:
        return CSVImportResult(
            events_created=0,
            events_updated=0,
            odds_created=0,
            odds_updated=0,
            errors=[f"Missing required columns: {', '.join(sorted(missing))}"],
        )

    events_created = 0
    events_updated = 0
    odds_created = 0
    odds_updated = 0
    errors: list[str] = []
    event_cache: dict[str, Event] = {}

    for row_num, row in enumerate(reader, start=2):
        try:
            normalized_row = {k.strip().lower(): (v.strip() if v else "") for k, v in row.items()}

            sport = normalized_row["sport"]
            league = normalized_row["league"]
            start_time_raw = normalized_row["start_time"]
            home_team = normalized_row["home_team"]
            away_team = normalized_row["away_team"]
            sportsbook = normalize_sportsbook(normalized_row["sportsbook"])
            market = normalize_market(normalized_row["market"])
            selection = normalized_row["selection"]
            american_odds = _parse_american(normalized_row["american_odds"])
            line = _parse_line(normalized_row.get("line"))
            timestamp = _parse_timestamp(normalized_row.get("timestamp"))

            if normalized_row.get("decimal_odds"):
                decimal_odds = float(normalized_row["decimal_odds"])
            else:
                decimal_odds = american_to_decimal(american_odds)

            start_time = date_parser.parse(start_time_raw)
            event_id = normalized_row.get("event_id") or build_event_id(
                sport, league, start_time.isoformat(), home_team, away_team
            )

            home_norm = normalize_team(home_team)
            away_norm = normalize_team(away_team)
            selection_norm = normalize_selection(selection, market, home_team, away_team)

            event = event_cache.get(event_id) or db.query(Event).filter(Event.event_id == event_id).first()
            if event:
                event.sport = sport
                event.league = league
                event.start_time = start_time
                event.home_team = home_team
                event.away_team = away_team
                event.home_team_normalized = home_norm
                event.away_team_normalized = away_norm
                if event_id not in event_cache:
                    events_updated += 1
            else:
                event = Event(
                    event_id=event_id,
                    sport=sport,
                    league=league,
                    start_time=start_time,
                    home_team=home_team,
                    away_team=away_team,
                    home_team_normalized=home_norm,
                    away_team_normalized=away_norm,
                )
                db.add(event)
                events_created += 1

            event_cache[event_id] = event

            existing_odds = (
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

            if existing_odds:
                existing_odds.selection = selection
                existing_odds.american_odds = american_odds
                existing_odds.decimal_odds = decimal_odds
                existing_odds.timestamp = timestamp
                odds_updated += 1
            else:
                db.add(
                    Odds(
                        event_id=event_id,
                        sportsbook=sportsbook,
                        market=market,
                        selection=selection,
                        selection_normalized=selection_norm,
                        line=line,
                        american_odds=american_odds,
                        decimal_odds=decimal_odds,
                        timestamp=timestamp,
                    )
                )
                odds_created += 1

        except Exception as exc:
            errors.append(f"Row {row_num}: {exc}")

    db.commit()

    return CSVImportResult(
        events_created=events_created,
        events_updated=events_updated,
        odds_created=odds_created,
        odds_updated=odds_updated,
        errors=errors,
    )
