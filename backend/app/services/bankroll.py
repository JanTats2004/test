def flat_stake(amount: float) -> float:
    return max(0.0, round(amount, 2))


def kelly_stake(
    bankroll: float,
    fair_probability: float,
    decimal_odds: float,
    fraction: float = 0.25,
) -> float:
    """
    Fractional Kelly criterion stake sizing.
    b = net odds (decimal - 1), p = fair win probability, q = 1 - p
    Kelly fraction = (b*p - q) / b
    """
    if bankroll <= 0 or decimal_odds <= 1:
        return 0.0

    b = decimal_odds - 1
    p = fair_probability
    q = 1 - p
    kelly = (b * p - q) / b

    if kelly <= 0:
        return 0.0

    stake = bankroll * kelly * fraction
    return max(0.0, round(stake, 2))


def suggested_stake(
    bankroll: float,
    fair_probability: float,
    decimal_odds: float,
    flat_amount: float,
    use_kelly: bool,
    kelly_fraction: float,
) -> tuple[float, str]:
    if use_kelly:
        return kelly_stake(bankroll, fair_probability, decimal_odds, kelly_fraction), "fractional_kelly"
    return flat_stake(flat_amount), "flat"
