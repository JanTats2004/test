from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Event, Odds
from app.schemas import EVResult, EVScanRequest
from app.services.bankroll import suggested_stake
from app.services.odds_utils import break_even_probability, calculate_ev
from app.services.vig import compute_fair_probabilities


def _is_stale(timestamp: datetime, stale_minutes: int) -> bool:
    now = datetime.now(timezone.utc)
    ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
    age_minutes = (now - ts).total_seconds() / 60
    return age_minutes > stale_minutes


def _market_key(event_id: str, market: str, line: float | None) -> str:
    if line is None:
        line_str = "none"
    elif market == "spread":
        line_str = f"{abs(line):.2f}"
    else:
        line_str = f"{line:.2f}"
    return f"{event_id}|{market}|{line_str}"


def scan_ev_opportunities(db: Session, request: EVScanRequest) -> list[EVResult]:
    stale_minutes = request.stale_minutes if request.stale_minutes is not None else 15

    query = db.query(Odds).join(Event, Odds.event_id == Event.event_id)
    if request.sport:
        query = query.filter(Event.sport == request.sport)
    if request.sportsbook:
        query = query.filter(Odds.sportsbook == request.sportsbook)
    if request.market:
        query = query.filter(Odds.market == request.market)

    all_odds = query.all()

    markets: dict[str, list[Odds]] = {}
    events_cache: dict[str, Event] = {}

    for odds_row in all_odds:
        event = odds_row.event
        events_cache[event.event_id] = event
        key = _market_key(odds_row.event_id, odds_row.market, odds_row.line)
        markets.setdefault(key, []).append(odds_row)

    results: list[EVResult] = []

    for _key, market_odds in markets.items():
        if len(market_odds) < 2:
            continue

        odds_dicts = [
            {
                "selection_normalized": o.selection_normalized,
                "decimal_odds": o.decimal_odds,
                "sportsbook": o.sportsbook,
            }
            for o in market_odds
        ]
        fair_probs = compute_fair_probabilities(odds_dicts)
        if len(fair_probs) < 2:
            continue

        books_in_market = len({o.sportsbook for o in market_odds})

        for odds_row in market_odds:
            fair_prob = fair_probs.get(odds_row.selection_normalized)
            if fair_prob is None:
                continue

            ev = calculate_ev(fair_prob, odds_row.decimal_odds)
            if ev < request.min_ev:
                continue

            if request.min_odds is not None and odds_row.american_odds < request.min_odds:
                continue
            if request.max_odds is not None and odds_row.american_odds > request.max_odds:
                continue

            stake, method = suggested_stake(
                bankroll=request.bankroll,
                fair_probability=fair_prob,
                decimal_odds=odds_row.decimal_odds,
                flat_amount=request.flat_stake,
                use_kelly=request.use_kelly,
                kelly_fraction=request.kelly_fraction,
            )

            event = events_cache[odds_row.event_id]
            results.append(
                EVResult(
                    event_id=event.event_id,
                    sport=event.sport,
                    league=event.league,
                    start_time=event.start_time,
                    home_team=event.home_team,
                    away_team=event.away_team,
                    market=odds_row.market,
                    selection=odds_row.selection,
                    line=odds_row.line,
                    sportsbook=odds_row.sportsbook,
                    american_odds=odds_row.american_odds,
                    decimal_odds=odds_row.decimal_odds,
                    fair_probability=round(fair_prob, 4),
                    break_even_probability=round(break_even_probability(odds_row.decimal_odds), 4),
                    ev_percent=round(ev * 100, 2),
                    suggested_stake=stake,
                    stake_method=method,
                    is_stale=_is_stale(odds_row.timestamp, stale_minutes),
                    last_updated=odds_row.timestamp,
                    books_in_market=books_in_market,
                )
            )

    results.sort(key=lambda r: r.ev_percent, reverse=True)
    return results
