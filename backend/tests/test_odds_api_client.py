import pytest
from unittest.mock import MagicMock, patch

from app.services.odds_api_client import (
    OddsAPIClient,
    OddsAPIError,
    flatten_odds_events,
)


SAMPLE_EVENTS = [
    {
        "id": "evt1",
        "sport_title": "NBA",
        "commence_time": "2026-07-03T23:00:00Z",
        "home_team": "Toronto Raptors",
        "away_team": "Boston Celtics",
        "bookmakers": [
            {
                "key": "fanduel",
                "title": "FanDuel",
                "last_update": "2026-07-03T20:00:00Z",
                "markets": [
                    {
                        "key": "h2h",
                        "last_update": "2026-07-03T20:00:00Z",
                        "outcomes": [
                            {"name": "Toronto Raptors", "price": 110},
                            {"name": "Boston Celtics", "price": -130},
                        ],
                    }
                ],
            }
        ],
    }
]


class TestOddsAPIClient:
    def test_not_configured_raises(self):
        client = OddsAPIClient(api_key="")
        with pytest.raises(OddsAPIError, match="ODDS_API_KEY"):
            client.fetch_sports()

    def test_normalize_regions_invalid(self):
        with pytest.raises(OddsAPIError, match="Unsupported region"):
            OddsAPIClient(api_key="test").normalize_regions("ca")

    def test_normalize_markets(self):
        client = OddsAPIClient(api_key="test")
        assert client.normalize_markets(["moneyline", "spread"]) == "h2h,spreads"

    def test_normalize_markets_invalid(self):
        with pytest.raises(OddsAPIError, match="Unsupported market"):
            OddsAPIClient(api_key="test").normalize_markets("props")

    def test_flatten_odds_events(self):
        rows = flatten_odds_events(SAMPLE_EVENTS)
        assert len(rows) == 2
        assert rows[0]["market"] == "moneyline"
        assert rows[0]["american_odds"] == 110
        assert rows[0]["fetched_at"]

    @patch("app.services.odds_api_client.httpx.Client")
    def test_fetch_odds_success(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_EVENTS
        mock_response.headers = {"x-requests-remaining": "450"}

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = OddsAPIClient(api_key="test-key")
        result = client.fetch_odds("basketball_nba", regions="us", markets="moneyline")

        assert result["event_count"] == 1
        assert result["row_count"] == 2
        assert result["requests_remaining"] == "450"

    @patch("app.services.odds_api_client.httpx.Client")
    def test_fetch_odds_invalid_key(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Invalid API key"}
        mock_response.text = "Unauthorized"
        mock_response.reason_phrase = "Unauthorized"

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = OddsAPIClient(api_key="bad-key")
        with pytest.raises(OddsAPIError, match="Invalid API key"):
            client.fetch_odds("basketball_nba")
