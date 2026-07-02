# Ontario EV Betting Scanner

A Windows desktop-ready application that compares odds across Ontario sportsbooks and identifies positive expected value (+EV) betting opportunities.

**This tool does not place bets, store passwords, or bypass any security measures.**

## Supported Sportsbooks

- theScore Bet
- FanDuel Ontario
- DraftKings Ontario
- Bet365 Ontario
- BetMGM Ontario
- Caesars Ontario

## Markets

- Moneyline
- Spread
- Totals
- Player props (planned for a future stage)

## Features

| Feature | Status |
|---------|--------|
| Manual CSV odds upload | Stage 1 |
| Team/market/book normalization | Done |
| Cross-book event matching | Done |
| Vig removal & fair probability | Done |
| EV calculation | Done |
| EV threshold filtering | Done |
| Stale odds flagging | Done |
| Last update timestamps | Done |
| Flat & fractional Kelly staking | Done |
| CSV export | Done |
| Sport/book/market/odds filters | Done |
| The Odds API integration | Stage 2 (scaffolded) |
| Real-time refresh | Stage 3 (planned) |
| Alerts | Stage 4 (planned) |
| Browser-assisted viewing (Playwright) | Stage 5 (planned) |

## EV Formula

For decimal odds:

```
EV = (fair_probability × decimal_odds) - 1
```

American to decimal conversion:
- Positive: `decimal = 1 + odds / 100`
- Negative: `decimal = 1 + 100 / abs(odds)`

**Example:** Fair probability 55%, odds +100 (decimal 2.00):
`EV = 0.55 × 2.00 - 1 = +10%`

Fair probability is estimated by averaging implied probabilities across books, then removing the vig so selections sum to 100%.

## Quick Start (Windows)

### Prerequisites

- Python 3.11+
- Node.js 18+ (for building the frontend)

### Run

Double-click or run from Command Prompt:

```bat
scripts\run.bat
```

Or in PowerShell:

```powershell
.\scripts\run.ps1
```

Open **http://localhost:8000** in your browser.

### First Use

1. Click **Upload Odds (CSV)** and select `samples/sample_odds.csv`
2. Set your **Min EV** threshold (default +2%)
3. Click **Scan for +EV Bets**
4. Review results and **Export CSV** if needed

## Development Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install pytest
uvicorn app.main:app --reload --port 8000
```

### Frontend (dev mode with hot reload)

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server runs at http://localhost:5173 and proxies API calls to port 8000.

### Run Tests

```bash
cd backend
source venv/bin/activate
pytest
```

## CSV Upload Format

Required columns:

| Column | Description |
|--------|-------------|
| `sport` | e.g. NBA, NHL |
| `league` | e.g. NBA, NHL |
| `start_time` | ISO datetime, e.g. `2026-07-03T19:30:00` |
| `home_team` | Home team name |
| `away_team` | Away team name |
| `sportsbook` | Book name (aliases accepted: fanduel, dk, etc.) |
| `market` | moneyline, spread, totals (aliases: ml, ou, etc.) |
| `selection` | Team name or Over/Under |
| `american_odds` | e.g. +150 or -110 |

Optional columns: `line`, `decimal_odds`, `timestamp`, `event_id`

See `samples/sample_odds.csv` for a working example.

## Stage 2: Odds API

For automated odds pulls, sign up at [The Odds API](https://the-odds-api.com/) and set your key:

```bash
cp .env.example backend/.env
# Edit backend/.env and set ODDS_API_KEY=your_key
```

Then use the **Refresh from Odds API** button in the UI, or call:

```
POST /api/odds-api/refresh/basketball_nba
```

This uses a licensed data provider — no scraping of sportsbook sites.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/settings` | App configuration |
| POST | `/api/import/csv` | Upload odds CSV |
| GET | `/api/ev/scan` | Scan for +EV bets |
| GET | `/api/ev/export` | Export results as CSV |
| GET | `/api/events` | List events |
| GET | `/api/odds` | List odds |
| POST | `/api/odds-api/refresh/{sport}` | Pull from Odds API |

## Data Model

**Event:** `event_id`, `sport`, `league`, `start_time`, `home_team`, `away_team`

**Odds:** `event_id`, `sportsbook`, `market`, `selection`, `line`, `american_odds`, `decimal_odds`, `timestamp`

**EV Result:** event info, market, selection, book, odds, fair/breakeven probability, EV%, suggested stake, staleness, last updated

## Architecture

```
backend/          FastAPI + SQLite
  app/
    models.py     SQLAlchemy models
    services/     EV engine, vig removal, normalization, CSV import
    routers/      API routes
frontend/         React + Vite UI
samples/          Sample CSV data
scripts/          Windows/Linux launchers
```

## Roadmap

- **Stage 1** — Manual CSV upload (current)
- **Stage 2** — The Odds API integration
- **Stage 3** — Scheduled real-time refresh
- **Stage 4** — Desktop alerts for +EV opportunities
- **Stage 5** — Optional Playwright browser display (view only, no auto-betting)

## Disclaimer

This software is for informational and educational purposes only. Always verify odds on the sportsbook before wagering. Gamble responsibly. Must be 19+ in Ontario.
