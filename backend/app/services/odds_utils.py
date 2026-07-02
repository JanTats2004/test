def american_to_decimal(american_odds: int) -> float:
    if american_odds == 0:
        raise ValueError("American odds cannot be zero")
    if american_odds > 0:
        return 1 + american_odds / 100
    return 1 + 100 / abs(american_odds)


def decimal_to_american(decimal_odds: float) -> int:
    if decimal_odds <= 1:
        raise ValueError("Decimal odds must be greater than 1")
    if decimal_odds >= 2:
        return round((decimal_odds - 1) * 100)
    return round(-100 / (decimal_odds - 1))


def implied_probability_from_decimal(decimal_odds: float) -> float:
    if decimal_odds <= 0:
        raise ValueError("Decimal odds must be positive")
    return 1 / decimal_odds


def implied_probability_from_american(american_odds: int) -> float:
    return implied_probability_from_decimal(american_to_decimal(american_odds))


def break_even_probability(decimal_odds: float) -> float:
    return implied_probability_from_decimal(decimal_odds)


def calculate_ev(fair_probability: float, decimal_odds: float) -> float:
    """Return EV as a decimal fraction (0.10 = +10%)."""
    return (fair_probability * decimal_odds) - 1
