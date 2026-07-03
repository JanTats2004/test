"""
Ontario EV Betting Scanner — Streamlit UI (beginner-friendly)

Run from the backend folder:
    streamlit run app.py

Requires ODDS_API_KEY in backend/.env for live odds.
Does NOT scrape sportsbooks or bypass any security.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Ensure backend package imports work when running streamlit run app.py
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")

from app.database import SessionLocal, init_db
from app.schemas import EVScanRequest
from app.services.ev_engine import scan_ev_opportunities
from app.services.odds_api import ingest_api_odds, is_configured
from app.services.odds_api_client import (
    SUPPORTED_REGIONS,
    OddsAPIClient,
    OddsAPIError,
)

st.set_page_config(
    page_title="Ontario EV Betting Scanner",
    page_icon="📊",
    layout="wide",
)

MARKET_OPTIONS = {
    "Moneyline": "moneyline",
    "Spread": "spread",
    "Totals": "totals",
}

REGION_LABELS = {
    "us": "US",
    "us2": "US (alt)",
    "uk": "UK",
    "eu": "EU",
    "au": "AU",
}


def format_american(odds: int | float | None) -> str:
    if odds is None:
        return ""
    odds = int(odds)
    return f"+{odds}" if odds > 0 else str(odds)


def init_session():
    init_db()
    if "odds_rows" not in st.session_state:
        st.session_state.odds_rows = []
    if "ev_results" not in st.session_state:
        st.session_state.ev_results = []
    if "last_fetch" not in st.session_state:
        st.session_state.last_fetch = None


def main():
    init_session()

    st.title("Ontario EV Betting Scanner")
    st.caption(
        "Compare sportsbook odds via **The Odds API** (licensed data). "
        "No scraping. No auto-betting."
    )

    # --- Sidebar ---
    with st.sidebar:
        st.header("Settings")
        api_ok = is_configured()
        if api_ok:
            st.success("Odds API key loaded from .env")
        else:
            st.error("No API key found")
            st.markdown(
                "1. Go to [the-odds-api.com](https://the-odds-api.com/)\n"
                "2. Sign up (free tier available)\n"
                "3. Copy your API key\n"
                "4. Edit `backend/.env`:\n"
                "```\nODDS_API_KEY=your_api_key_here\n```"
            )

        st.divider()
        min_ev_pct = st.number_input("Min EV (%)", min_value=0.0, max_value=50.0, value=2.0, step=0.5)
        bankroll = st.number_input("Bankroll ($)", min_value=0.0, value=1000.0, step=100.0)
        flat_stake = st.number_input("Flat stake ($)", min_value=0.0, value=25.0, step=5.0)
        use_kelly = st.checkbox("Use fractional Kelly", value=False)
        kelly_fraction = st.slider("Kelly fraction", 0.05, 1.0, 0.25, 0.05, disabled=not use_kelly)

    # --- Fetch odds section ---
    st.subheader("1. Fetch live odds")

    col1, col2, col3 = st.columns([2, 1, 2])

    client = OddsAPIClient()

    with col1:
        sport_options: dict[str, str] = {}
        if api_ok:
            try:
                sports = client.fetch_sports()
                sport_options = {f"{s['title']} ({s['key']})": s["key"] for s in sports if s.get("active")}
            except OddsAPIError as exc:
                st.warning(f"Could not load sports: {exc}")
        sport_label = st.selectbox(
            "Sport",
            options=list(sport_options.keys()) if sport_options else ["Configure API key first"],
            disabled=not sport_options,
        )
        sport_key = sport_options.get(sport_label, "")

    with col2:
        region = st.selectbox(
            "Region",
            options=list(SUPPORTED_REGIONS),
            format_func=lambda r: REGION_LABELS.get(r, r),
            index=0,
        )

    with col3:
        selected_markets = st.multiselect(
            "Markets",
            options=list(MARKET_OPTIONS.keys()),
            default=["Moneyline", "Spread", "Totals"],
        )
        market_values = [MARKET_OPTIONS[m] for m in selected_markets]

    fetch_clicked = st.button("Fetch odds from The Odds API", type="primary", disabled=not api_ok)

    if fetch_clicked and sport_key and market_values:
        with st.spinner(f"Fetching {sport_key} odds…"):
            try:
                result = client.fetch_odds(
                    sport_key=sport_key,
                    regions=region,
                    markets=market_values,
                    odds_format="american",
                )
                st.session_state.odds_rows = result["rows"]
                st.session_state.last_fetch = result["fetched_at"]

                db = SessionLocal()
                try:
                    ingest = ingest_api_odds(db, result["events"])
                finally:
                    db.close()

                remaining = result.get("requests_remaining")
                msg = (
                    f"Fetched **{result['row_count']}** odds lines from "
                    f"**{result['event_count']}** events. "
                    f"Saved {ingest['odds_created']} new / {ingest['odds_updated']} updated."
                )
                if remaining:
                    msg += f" API requests remaining: {remaining}"
                st.success(msg)
            except OddsAPIError as exc:
                st.error(str(exc))

    # --- Odds table ---
    st.subheader("2. Odds table")

    if st.session_state.last_fetch:
        st.caption(f"Last fetched: {st.session_state.last_fetch}")

    if st.session_state.odds_rows:
        df = pd.DataFrame(st.session_state.odds_rows)
        display_cols = [
            "commence_time",
            "away_team",
            "home_team",
            "sportsbook",
            "market",
            "selection",
            "line",
            "american_odds",
            "last_update",
        ]
        display_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
    else:
        st.info("Click **Fetch odds** to load live odds into the table.")

    # --- EV scan ---
    st.subheader("3. +EV opportunities")

    scan_clicked = st.button("Calculate +EV bets", disabled=not st.session_state.odds_rows)

    if scan_clicked:
        db = SessionLocal()
        try:
            request = EVScanRequest(
                min_ev=min_ev_pct / 100,
                bankroll=bankroll,
                flat_stake=flat_stake,
                use_kelly=use_kelly,
                kelly_fraction=kelly_fraction,
            )
            results = scan_ev_opportunities(db, request)
            st.session_state.ev_results = results
        finally:
            db.close()

    if st.session_state.ev_results:
        ev_rows = []
        for r in st.session_state.ev_results:
            ev_rows.append(
                {
                    "EV %": r.ev_percent,
                    "Event": f"{r.away_team} @ {r.home_team}",
                    "Market": r.market,
                    "Selection": r.selection,
                    "Line": r.line,
                    "Book": r.sportsbook,
                    "Odds": format_american(r.american_odds),
                    "Fair Prob": round(r.fair_probability * 100, 1),
                    "Stake $": r.suggested_stake,
                    "Stale": r.is_stale,
                    "Updated": r.last_updated,
                }
            )
        st.dataframe(pd.DataFrame(ev_rows), use_container_width=True, hide_index=True)
        st.caption(f"Found {len(ev_rows)} opportunities at ≥ {min_ev_pct}% EV")
    elif st.session_state.odds_rows:
        st.info("Click **Calculate +EV bets** to scan for positive expected value.")

    st.divider()
    st.markdown(
        "**Disclaimer:** Informational use only. Verify odds on the sportsbook before wagering. "
        "Gamble responsibly. 19+ in Ontario."
    )


if __name__ == "__main__":
    main()
