import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CSVImportResult, EVScanRequest, EVResult, ScanSummary
from app.services.csv_importer import import_odds_csv
from app.services.ev_engine import scan_ev_opportunities

router = APIRouter(prefix="/api/ev", tags=["ev"])


@router.post("/scan", response_model=ScanSummary)
def scan_ev(request: EVScanRequest, db: Session = Depends(get_db)):
    results = scan_ev_opportunities(db, request)
    return ScanSummary(
        total_opportunities=len(results),
        filtered_opportunities=len(results),
        scan_timestamp=datetime.utcnow(),
        results=results,
    )


@router.get("/scan", response_model=ScanSummary)
def scan_ev_get(
    min_ev: float = 0.02,
    min_odds: int | None = None,
    max_odds: int | None = None,
    sport: str | None = None,
    sportsbook: str | None = None,
    market: str | None = None,
    stale_minutes: int | None = None,
    bankroll: float = 1000.0,
    flat_stake: float = 25.0,
    use_kelly: bool = False,
    kelly_fraction: float = 0.25,
    db: Session = Depends(get_db),
):
    request = EVScanRequest(
        min_ev=min_ev,
        min_odds=min_odds,
        max_odds=max_odds,
        sport=sport,
        sportsbook=sportsbook,
        market=market,
        stale_minutes=stale_minutes,
        bankroll=bankroll,
        flat_stake=flat_stake,
        use_kelly=use_kelly,
        kelly_fraction=kelly_fraction,
    )
    results = scan_ev_opportunities(db, request)
    return ScanSummary(
        total_opportunities=len(results),
        filtered_opportunities=len(results),
        scan_timestamp=datetime.utcnow(),
        results=results,
    )


@router.get("/export")
def export_ev_csv(
    min_ev: float = 0.02,
    min_odds: int | None = None,
    max_odds: int | None = None,
    sport: str | None = None,
    sportsbook: str | None = None,
    market: str | None = None,
    stale_minutes: int | None = None,
    bankroll: float = 1000.0,
    flat_stake: float = 25.0,
    use_kelly: bool = False,
    kelly_fraction: float = 0.25,
    db: Session = Depends(get_db),
):
    request = EVScanRequest(
        min_ev=min_ev,
        min_odds=min_odds,
        max_odds=max_odds,
        sport=sport,
        sportsbook=sportsbook,
        market=market,
        stale_minutes=stale_minutes,
        bankroll=bankroll,
        flat_stake=flat_stake,
        use_kelly=use_kelly,
        kelly_fraction=kelly_fraction,
    )
    results = scan_ev_opportunities(db, request)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "event_id",
            "sport",
            "league",
            "start_time",
            "home_team",
            "away_team",
            "market",
            "selection",
            "line",
            "sportsbook",
            "american_odds",
            "decimal_odds",
            "fair_probability",
            "break_even_probability",
            "ev_percent",
            "suggested_stake",
            "stake_method",
            "is_stale",
            "last_updated",
            "books_in_market",
        ]
    )
    for r in results:
        writer.writerow(
            [
                r.event_id,
                r.sport,
                r.league,
                r.start_time.isoformat(),
                r.home_team,
                r.away_team,
                r.market,
                r.selection,
                r.line if r.line is not None else "",
                r.sportsbook,
                r.american_odds,
                r.decimal_odds,
                r.fair_probability,
                r.break_even_probability,
                r.ev_percent,
                r.suggested_stake,
                r.stake_method,
                r.is_stale,
                r.last_updated.isoformat(),
                r.books_in_market,
            ]
        )

    output.seek(0)
    filename = f"ev_opportunities_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
