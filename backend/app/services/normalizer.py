import re
import unicodedata


TEAM_ALIASES: dict[str, str] = {
    "tor raptors": "toronto raptors",
    "raptors": "toronto raptors",
    "toronto": "toronto raptors",
    "bos celtics": "boston celtics",
    "celtics": "boston celtics",
    "boston": "boston celtics",
    "la lakers": "los angeles lakers",
    "lakers": "los angeles lakers",
    "la clippers": "los angeles clippers",
    "clippers": "los angeles clippers",
    "gs warriors": "golden state warriors",
    "warriors": "golden state warriors",
    "golden state": "golden state warriors",
    "ny knicks": "new york knicks",
    "knicks": "new york knicks",
    "ny rangers": "new york rangers",
    "rangers": "new york rangers",
    "tor maple leafs": "toronto maple leafs",
    "maple leafs": "toronto maple leafs",
    "leafs": "toronto maple leafs",
    "mtl canadiens": "montreal canadiens",
    "canadiens": "montreal canadiens",
    "habs": "montreal canadiens",
    "over": "over",
    "under": "under",
    "o": "over",
    "u": "under",
}

MARKET_ALIASES: dict[str, str] = {
    "ml": "moneyline",
    "money line": "moneyline",
    "moneyline": "moneyline",
    "h2h": "moneyline",
    "head to head": "moneyline",
    "spread": "spread",
    "point spread": "spread",
    "handicap": "spread",
    "ats": "spread",
    "total": "totals",
    "totals": "totals",
    "over/under": "totals",
    "overunder": "totals",
    "ou": "totals",
    "game total": "totals",
}

SPORTSBOOK_ALIASES: dict[str, str] = {
    "score bet": "theScore Bet",
    "thescore bet": "theScore Bet",
    "thescore": "theScore Bet",
    "fanduel": "FanDuel Ontario",
    "fanduel ontario": "FanDuel Ontario",
    "fd": "FanDuel Ontario",
    "draftkings": "DraftKings Ontario",
    "draftkings ontario": "DraftKings Ontario",
    "dk": "DraftKings Ontario",
    "bet365": "Bet365 Ontario",
    "bet365 ontario": "Bet365 Ontario",
    "betmgm": "BetMGM Ontario",
    "betmgm ontario": "BetMGM Ontario",
    "mgm": "BetMGM Ontario",
    "caesars": "Caesars Ontario",
    "caesars ontario": "Caesars Ontario",
    "william hill": "Caesars Ontario",
}


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_key(value: str) -> str:
    cleaned = _strip_accents(value.strip().lower())
    cleaned = re.sub(r"[^\w\s.-]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_team(name: str) -> str:
    key = normalize_key(name)
    return TEAM_ALIASES.get(key, key)


def normalize_market(market: str) -> str:
    key = normalize_key(market)
    return MARKET_ALIASES.get(key, key)


def normalize_sportsbook(book: str) -> str:
    key = normalize_key(book)
    return SPORTSBOOK_ALIASES.get(key, book.strip())


def normalize_selection(selection: str, market: str, home_team: str, away_team: str) -> str:
    key = normalize_key(selection)
    market_norm = normalize_market(market)

    if market_norm == "totals":
        if key in {"over", "o"}:
            return "over"
        if key in {"under", "u"}:
            return "under"
        return key

    home_norm = normalize_team(home_team)
    away_norm = normalize_team(away_team)

    if key in {home_norm, normalize_key(home_team)}:
        return home_norm
    if key in {away_norm, normalize_key(away_team)}:
        return away_norm
    if key in {"home", "h"}:
        return home_norm
    if key in {"away", "a"}:
        return away_norm
    if key in {"draw", "tie", "x"}:
        return "draw"

    return normalize_team(selection)


def build_event_id(sport: str, league: str, start_time_iso: str, home_team: str, away_team: str) -> str:
    home = normalize_team(home_team)
    away = normalize_team(away_team)
    sport_key = normalize_key(sport)
    league_key = normalize_key(league)
    time_key = start_time_iso.replace(":", "").replace("-", "").replace("T", "").replace("Z", "")[:12]
    return f"{sport_key}_{league_key}_{time_key}_{home}_{away}"
