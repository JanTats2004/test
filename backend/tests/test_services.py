import pytest

from app.services.bankroll import flat_stake, kelly_stake
from app.services.odds_utils import american_to_decimal, calculate_ev, decimal_to_american
from app.services.normalizer import normalize_market, normalize_sportsbook, normalize_team
from app.services.vig import compute_fair_probabilities, remove_vig_from_averages


class TestOddsUtils:
    def test_american_to_decimal_positive(self):
        assert american_to_decimal(100) == pytest.approx(2.0)

    def test_american_to_decimal_negative(self):
        assert american_to_decimal(-200) == pytest.approx(1.5)

    def test_decimal_to_american_roundtrip(self):
        assert decimal_to_american(american_to_decimal(150)) == 150

    def test_ev_formula_example(self):
        # fair prob 55%, decimal odds 2.00 => EV = +10%
        ev = calculate_ev(0.55, 2.0)
        assert ev == pytest.approx(0.10)


class TestVigRemoval:
    def test_remove_vig_normalizes_to_one(self):
        raw = {"team_a": 0.55, "team_b": 0.55}
        fair = remove_vig_from_averages(raw)
        assert sum(fair.values()) == pytest.approx(1.0)
        assert fair["team_a"] == pytest.approx(0.5)

    def test_compute_fair_probabilities(self):
        odds = [
            {"selection_normalized": "home", "decimal_odds": 2.0},
            {"selection_normalized": "home", "decimal_odds": 2.1},
            {"selection_normalized": "away", "decimal_odds": 1.9},
            {"selection_normalized": "away", "decimal_odds": 1.85},
        ]
        fair = compute_fair_probabilities(odds)
        assert sum(fair.values()) == pytest.approx(1.0)
        assert "home" in fair
        assert "away" in fair


class TestNormalizer:
    def test_normalize_team_alias(self):
        assert normalize_team("Raptors") == "toronto raptors"

    def test_normalize_market(self):
        assert normalize_market("ML") == "moneyline"
        assert normalize_market("over/under") == "totals"

    def test_normalize_sportsbook(self):
        assert normalize_sportsbook("fanduel") == "FanDuel Ontario"


class TestBankroll:
    def test_flat_stake(self):
        assert flat_stake(25.0) == 25.0

    def test_kelly_positive_ev(self):
        stake = kelly_stake(1000, 0.55, 2.0, fraction=0.25)
        assert stake > 0

    def test_kelly_negative_ev_returns_zero(self):
        stake = kelly_stake(1000, 0.40, 2.0, fraction=0.25)
        assert stake == 0.0
