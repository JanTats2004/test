from pydantic import BaseModel, Field


class OddsAPIFetchRequest(BaseModel):
    sport_key: str
    regions: str = Field(default="us", description="Comma-separated: us, us2, uk, eu, au")
    markets: str = Field(default="moneyline,spread,totals", description="Comma-separated market names")


class OddsAPIFetchResponse(BaseModel):
    sport_key: str
    regions: str
    markets: str
    event_count: int
    row_count: int
    events_created: int
    odds_created: int
    odds_updated: int
    fetched_at: str
    requests_remaining: str | None = None
