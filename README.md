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
| The Odds API integration | Stage 2 (done) |
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

- **Python 3.11+** — [python.org/downloads](https://www.python.org/downloads/) (check "Add Python to PATH" during install)
- **Node.js 18+** — only needed for the React UI (`scripts\run.bat`); not needed for Streamlit (`scripts\run_streamlit.bat`)

---

## Connect The Odds API (Step by Step)

### 1. Create an account and get your API key

1. Go to **[https://the-odds-api.com/](https://the-odds-api.com/)**
2. Click **Get Started** or **Sign Up**
3. Create a free account (free tier includes 500 requests/month)
4. After login, open your **Dashboard** or **API Keys** page
5. Copy your API key (a long string like `a1b2c3d4e5f6...`)

This is a **licensed odds data provider**. The app uses their official API — it does **not** scrape sportsbook websites.

### 2. Store your API key safely in `.env`

Your key must **never** be committed to git or hardcoded in Python files.

```bat
cd backend
copy .env.example .env
notepad .env
```

Set exactly one line (replace with your real key):

```
ODDS_API_KEY=your_api_key_here
```

**Safety rules:**
- `.env` is listed in `.gitignore` — it stays on your PC only
- Do not share `.env` or paste your key in chat/issues
- Use `backend/.env.example` as the template (no real key inside)

### 3. Install dependencies

```bat
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

`python-dotenv` is included — it loads `ODDS_API_KEY` from `.env` automatically.

### 4. Run the app and fetch odds

**Option A — Streamlit (easiest for beginners, Python only):**

```bat
scripts\run_streamlit.bat
```

Open **http://localhost:8501**, then:
1. Choose a **Sport**
2. Choose a **Region** (`us`, `us2`, `uk`, `eu`, `au`)
3. Select **Markets** (Moneyline, Spread, Totals)
4. Click **Fetch odds from The Odds API**
5. Review the odds table
6. Click **Calculate +EV bets**

**Option B — Full React UI:**

```bat
scripts\run.bat
```

Open **http://localhost:8000**, use the **Fetch Live Odds** section the same way.

### 5. What the API client does

File: `backend/app/services/odds_api_client.py`

- Loads `ODDS_API_KEY` from `backend/.env` via `python-dotenv`
- Calls `https://api.the-odds-api.com/v4`
- Returns **American odds** format
- Supports regions: `us`, `us2`, `uk`, `eu`, `au`
- Pulls **moneyline**, **spread**, and **totals**
- Attaches **timestamps** (`last_update`, `fetched_at`)
- Handles errors (invalid key, rate limits, network failures)

---

## Run on Windows (both options)

### Option A: Streamlit UI (recommended for beginners)

```bat
scripts\run_streamlit.bat
```

Browser: **http://localhost:8501**

### Option B: React + FastAPI UI

```bat
scripts\run.bat
```

Browser: **http://localhost:8000**

### First use without API key (CSV only)

1. Click **Upload Odds (CSV)** and select `samples/sample_odds.csv`
2. Set **Min EV** (default +2%)
3. Click **Scan for +EV Bets**

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

## Stage 2: Odds API (implemented)

The Odds API client lives at `backend/app/services/odds_api_client.py`.

Example usage in Python:

```python
from app.services.odds_api_client import OddsAPIClient

client = OddsAPIClient()
sports = client.fetch_sports()
result = client.fetch_odds(
    sport_key="basketball_nba",
    regions="us",
    markets=["moneyline", "spread", "totals"],
    odds_format="american",
)
print(result["row_count"], "odds lines")
```

### API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/odds-api/sports` | List available sports |
| GET | `/api/odds-api/regions` | List supported regions |
| POST | `/api/odds-api/fetch` | Fetch odds and save to DB |
| GET | `/api/odds-api/preview` | Fetch odds for table preview |
| POST | `/api/odds-api/refresh/{sport}` | Fetch odds (legacy) |

This uses a licensed data provider — **no scraping** of sportsbook sites.

## Data Model

**Event:** `event_id`, `sport`, `league`, `start_time`, `home_team`, `away_team`

**Odds:** `event_id`, `sportsbook`, `market`, `selection`, `line`, `american_odds`, `decimal_odds`, `timestamp`

**EV Result:** event info, market, selection, book, odds, fair/breakeven probability, EV%, suggested stake, staleness, last updated

## Architecture

```
backend/
  app.py                          Streamlit UI (run: streamlit run app.py)
  app/
    services/
      odds_api_client.py          The Odds API client (dotenv, regions, errors)
      odds_api.py                 Ingest API data into SQLite
      ev_engine.py                EV calculation
frontend/                         React + Vite UI
samples/                          Sample CSV data
scripts/
  run.bat                         Windows: React + FastAPI
  run_streamlit.bat               Windows: Streamlit only (beginner)
```

## Roadmap

- **Stage 1** — Manual CSV upload ✅
- **Stage 2** — The Odds API integration ✅
- **Stage 3** — Scheduled real-time refresh
- **Stage 4** — Desktop alerts for +EV opportunities
- **Stage 5** — Optional Playwright browser display (view only, no auto-betting)

## Disclaimer

This software is for informational and educational purposes only. Always verify odds on the sportsbook before wagering. Gamble responsibly. Must be 19+ in Ontario.
