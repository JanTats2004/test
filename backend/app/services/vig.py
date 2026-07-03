from collections import defaultdict

from app.services.odds_utils import implied_probability_from_decimal


def remove_vig_from_averages(selection_avg_probs: dict[str, float]) -> dict[str, float]:
    """
    Given average implied probabilities per selection (which include vig),
    normalize so fair probabilities sum to 1.0.
    """
    if not selection_avg_probs:
        return {}

    total = sum(selection_avg_probs.values())
    if total <= 0:
        return {k: 0.0 for k in selection_avg_probs}

    return {selection: prob / total for selection, prob in selection_avg_probs.items()}


def compute_fair_probabilities(
    market_odds: list[dict],
) -> dict[str, float]:
    """
    Compute fair probability per selection from a list of odds dicts with keys:
    selection_normalized, decimal_odds
    """
    selection_probs: dict[str, list[float]] = defaultdict(list)

    for row in market_odds:
        implied = implied_probability_from_decimal(row["decimal_odds"])
        selection_probs[row["selection_normalized"]].append(implied)

    avg_probs = {
        selection: sum(probs) / len(probs)
        for selection, probs in selection_probs.items()
        if probs
    }

    return remove_vig_from_averages(avg_probs)
