"""
The Odds API client for licensed sportsbook odds data.

Uses https://the-odds-api.com/ — does NOT scrape sportsbook websites.
API key is loaded from backend/.env via python-dotenv. Never hardcode keys.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"

load_dotenv(ENV_FILE)

BASE_URL = "https://api.the-odds-api.com/v4"
DEFAULT_TIMEOUT = 30.0

SUPPORTED_REGIONS = ("us", "us2", "uk", "eu", "au")

# App market names -> The Odds API market keys
MARKET_TO_API: dict[str, str] = {
    "moneyline": "h2h",
    "spread": "spreads",
    "totals": "totals",
    "h2h": "h2h",
    "spreads": "spreads",
}

API_TO_MARKET: dict[str, str] = {
    "h2h": "moneyline",
    "spreads": "spread",
    "totals": "totals",
}


class OddsAPIError(Exception):
    """Raised when The Odds API returns an error or the request fails."""


class OddsAPIClient:
    """Client for The Odds API v4."""

    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL):
        self.api_key = (api_key or os.getenv("ODDS_API_KEY", "")).strip()
        self.base_url = base_url.rstrip("/")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _require_key(self) -> None:
        if not self.is_configured:
            raise OddsAPIError(
                "ODDS_API_KEY is not set. Add it to backend/.env:\n"
                "  ODDS_API_KEY=your_api_key_here"
            )

    def _handle_response(self, response: httpx.Response) -> Any:
        if response.status_code == 200:
            return response.json()

        try:
            body = response.json()
            detail = body.get("message") or body.get("error") or str(body)
        except Exception:
            detail = response.text or response.reason_phrase

        if response.status_code == 401:
            raise OddsAPIError("Invalid API key. Check ODDS_API_KEY in backend/.env.")
        if response.status_code == 429:
            raise OddsAPIError("Rate limit exceeded. Wait and try again, or upgrade your Odds API plan.")
        if response.status_code == 422:
            raise OddsAPIError(f"Invalid request: {detail}")
        raise OddsAPIError(f"Odds API error ({response.status_code}): {detail}")

    @staticmethod
    def normalize_regions(regions: str | list[str]) -> str:
        if isinstance(regions, str):
            region_list = [r.strip().lower() for r in regions.split(",") if r.strip()]
        else:
            region_list = [r.strip().lower() for r in regions]

        invalid = [r for r in region_list if r not in SUPPORTED_REGIONS]
        if invalid:
            raise OddsAPIError(
                f"Unsupported region(s): {', '.join(invalid)}. "
                f"Use: {', '.join(SUPPORTED_REGIONS)}"
            )
        if not region_list:
            raise OddsAPIError("At least one region is required.")
        return ",".join(region_list)

    @staticmethod
    def normalize_markets(markets: str | list[str]) -> str:
        if isinstance(markets, str):
            market_list = [m.strip().lower() for m in markets.split(",") if m.strip()]
        else:
            market_list = [m.strip().lower() for m in markets]

        api_keys: list[str] = []
        for market in market_list:
            api_key = MARKET_TO_API.get(market)
            if not api_key:
                raise OddsAPIError(
                    f"Unsupported market: {market}. "
                    f"Use: moneyline, spread, totals (or h2h, spreads, totals)."
                )
            if api_key not in api_keys:
                api_keys.append(api_key)

        return ",".join(api_keys)

    def fetch_sports(self, all_sports: bool = False) -> list[dict]:
        """List in-season sports available from The Odds API."""
        self._require_key()
        params: dict[str, str | bool] = {"apiKey": self.api_key}
        if all_sports:
            params["all"] = "true"

        try:
            with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                response = client.get(f"{self.base_url}/sports", params=params)
        except httpx.TimeoutException as exc:
            raise OddsAPIError("Request timed out while fetching sports list.") from exc
        except httpx.HTTPError as exc:
            raise OddsAPIError(f"Network error fetching sports: {exc}") from exc

        return self._handle_response(response)

    def fetch_odds(
        self,
        sport_key: str,
        regions: str | list[str] = "us",
        markets: str | list[str] = ("moneyline", "spread", "totals"),
        odds_format: str = "american",
    ) -> dict[str, Any]:
        """
        Fetch live/upcoming odds for a sport.

        Returns a dict with:
          - events: raw API event list
          - rows: flattened odds rows with timestamps
          - fetched_at: UTC ISO timestamp
          - requests_remaining: from response headers (if provided)
        """
        self._require_key()
        regions_param = self.normalize_regions(regions)
        markets_param = self.normalize_markets(markets)

        params = {
            "apiKey": self.api_key,
            "regions": regions_param,
            "markets": markets_param,
            "oddsFormat": odds_format,
        }

        try:
            with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                response = client.get(
                    f"{self.base_url}/sports/{sport_key}/odds",
                    params=params,
                )
        except httpx.TimeoutException as exc:
            raise OddsAPIError(f"Request timed out while fetching odds for {sport_key}.") from exc
        except httpx.HTTPError as exc:
            raise OddsAPIError(f"Network error fetching odds: {exc}") from exc

        events = self._handle_response(response)
        fetched_at = datetime.now(timezone.utc)
        rows = flatten_odds_events(events, fetched_at=fetched_at)

        return {
            "sport_key": sport_key,
            "regions": regions_param,
            "markets": markets_param,
            "odds_format": odds_format,
            "events": events,
            "rows": rows,
            "event_count": len(events),
            "row_count": len(rows),
            "fetched_at": fetched_at.isoformat(),
            "requests_remaining": response.headers.get("x-requests-remaining"),
            "requests_used": response.headers.get("x-requests-used"),
        }


def flatten_odds_events(events: list[dict], fetched_at: datetime | None = None) -> list[dict]:
    """Convert nested API events into flat rows for tables and database import."""
    fetched_at = fetched_at or datetime.now(timezone.utc)
    fetched_iso = fetched_at.isoformat()
    rows: list[dict] = []

    for event in events:
        event_id = event.get("id", "")
        sport_title = event.get("sport_title", "")
        commence_time = event.get("commence_time", "")
        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")

        for bookmaker in event.get("bookmakers", []):
            book_key = bookmaker.get("key", "")
            book_title = bookmaker.get("title", book_key)
            last_update = bookmaker.get("last_update") or fetched_iso

            for market in bookmaker.get("markets", []):
                market_key = market.get("key", "")
                market_name = API_TO_MARKET.get(market_key, market_key)
                market_last_update = market.get("last_update") or last_update

                for outcome in market.get("outcomes", []):
                    rows.append(
                        {
                            "event_id": event_id,
                            "sport": sport_title,
                            "commence_time": commence_time,
                            "home_team": home_team,
                            "away_team": away_team,
                            "sportsbook_key": book_key,
                            "sportsbook": book_title,
                            "market": market_name,
                            "market_key": market_key,
                            "selection": outcome.get("name", ""),
                            "line": outcome.get("point"),
                            "american_odds": outcome.get("price"),
                            "last_update": market_last_update,
                            "fetched_at": fetched_iso,
                        }
                    )

    return rows


# Module-level singleton for convenience
_client: OddsAPIClient | None = None


def get_client() -> OddsAPIClient:
    global _client
    if _client is None:
        _client = OddsAPIClient()
    return _client
