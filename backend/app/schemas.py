from datetime import datetime

from pydantic import BaseModel, Field


class EventOut(BaseModel):
    event_id: str
    sport: str
    league: str
    start_time: datetime
    home_team: str
    away_team: str

    model_config = {"from_attributes": True}


class OddsOut(BaseModel):
    event_id: str
    sportsbook: str
    market: str
    selection: str
    line: float | None
    american_odds: int
    decimal_odds: float
    timestamp: datetime

    model_config = {"from_attributes": True}


class EVResult(BaseModel):
    event_id: str
    sport: str
    league: str
    start_time: datetime
    home_team: str
    away_team: str
    market: str
    selection: str
    line: float | None
    sportsbook: str
    american_odds: int
    decimal_odds: float
    fair_probability: float
    break_even_probability: float
    ev_percent: float
    suggested_stake: float
    stake_method: str
    is_stale: bool
    last_updated: datetime
    books_in_market: int


class EVScanRequest(BaseModel):
    min_ev: float = Field(default=0.02, description="Minimum EV threshold as decimal (0.02 = +2%)")
    min_odds: int | None = Field(default=None, description="Minimum American odds filter")
    max_odds: int | None = Field(default=None, description="Maximum American odds filter")
    sport: str | None = None
    sportsbook: str | None = None
    market: str | None = None
    stale_minutes: int | None = None
    bankroll: float = 1000.0
    flat_stake: float = 25.0
    use_kelly: bool = False
    kelly_fraction: float = 0.25


class CSVImportResult(BaseModel):
    events_created: int
    events_updated: int
    odds_created: int
    odds_updated: int
    errors: list[str]


class AppSettingsOut(BaseModel):
    sportsbooks: list[str]
    markets: list[str]
    stale_odds_minutes: int
    default_ev_threshold: float
    default_bankroll: float
    default_flat_stake: float
    default_kelly_fraction: float
    odds_api_configured: bool


class ScanSummary(BaseModel):
    total_opportunities: int
    filtered_opportunities: int
    scan_timestamp: datetime
    results: list[EVResult]
