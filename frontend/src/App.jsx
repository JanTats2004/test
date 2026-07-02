import { useCallback, useEffect, useState } from 'react'
import { exportEVUrl, fetchSettings, refreshOddsAPI, scanEV, uploadCSV } from './api'

function formatOdds(american) {
  return american > 0 ? `+${american}` : String(american)
}

function formatPct(value) {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

function formatProb(value) {
  return `${(value * 100).toFixed(1)}%`
}

function formatDate(iso) {
  return new Date(iso).toLocaleString()
}

const DEFAULT_FILTERS = {
  min_ev: 0.02,
  min_odds: '',
  max_odds: '',
  sport: '',
  sportsbook: '',
  market: '',
  stale_minutes: 15,
  bankroll: 1000,
  flat_stake: 25,
  use_kelly: false,
  kelly_fraction: 0.25,
}

export default function App() {
  const [settings, setSettings] = useState(null)
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const [results, setResults] = useState([])
  const [scanTime, setScanTime] = useState(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)
  const [messageType, setMessageType] = useState('info')

  const showMessage = (text, type = 'info') => {
    setMessage(text)
    setMessageType(type)
  }

  useEffect(() => {
    fetchSettings()
      .then((s) => {
        setSettings(s)
        setFilters((f) => ({
          ...f,
          min_ev: s.default_ev_threshold,
          bankroll: s.default_bankroll,
          flat_stake: s.default_flat_stake,
          kelly_fraction: s.default_kelly_fraction,
          stale_minutes: s.stale_odds_minutes,
        }))
      })
      .catch(() => showMessage('Could not connect to backend. Is the server running?', 'error'))
  }, [])

  const buildScanParams = useCallback(() => {
    const params = { ...filters }
    if (!params.min_odds) delete params.min_odds
    else params.min_odds = Number(params.min_odds)
    if (!params.max_odds) delete params.max_odds
    else params.max_odds = Number(params.max_odds)
    if (!params.sport) delete params.sport
    if (!params.sportsbook) delete params.sportsbook
    if (!params.market) delete params.market
    params.bankroll = Number(params.bankroll)
    params.flat_stake = Number(params.flat_stake)
    params.min_ev = Number(params.min_ev)
    params.stale_minutes = Number(params.stale_minutes)
    params.kelly_fraction = Number(params.kelly_fraction)
    return params
  }, [filters])

  const handleScan = async () => {
    setLoading(true)
    setMessage(null)
    try {
      const data = await scanEV(buildScanParams())
      setResults(data.results)
      setScanTime(data.scan_timestamp)
      showMessage(`Found ${data.results.length} +EV opportunities`, 'success')
    } catch {
      showMessage('Scan failed. Check backend connection.', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setLoading(true)
    setMessage(null)
    try {
      const result = await uploadCSV(file)
      const summary = `Imported: ${result.odds_created} new odds, ${result.odds_updated} updated. Events: ${result.events_created} new, ${result.events_updated} updated.`
      if (result.errors.length) {
        showMessage(`${summary} Warnings: ${result.errors.join('; ')}`, 'info')
      } else {
        showMessage(summary, 'success')
      }
      await handleScan()
    } catch {
      showMessage('CSV upload failed. Check file format.', 'error')
    } finally {
      setLoading(false)
      e.target.value = ''
    }
  }

  const handleExport = () => {
    window.open(exportEVUrl(buildScanParams()), '_blank')
  }

  const handleApiRefresh = async () => {
    setLoading(true)
    setMessage(null)
    try {
      const result = await refreshOddsAPI('basketball_nba')
      showMessage(`API refresh: ${result.odds_created} odds, ${result.events_created} events from ${result.events_in_response} API events`, 'success')
      await handleScan()
    } catch (err) {
      showMessage(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  const updateFilter = (key, value) => {
    setFilters((f) => ({ ...f, [key]: value }))
  }

  const sports = settings ? [...new Set(['NBA', 'NHL', 'NFL', 'MLB', 'NCAAB'])] : []

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Ontario EV Betting Scanner</h1>
          <p>Compare odds across Ontario sportsbooks and find positive expected value bets</p>
        </div>
        <span className="badge stage">Stage 1 — CSV Upload</span>
      </header>

      <div className="grid-2">
        <section className="card">
          <h2>Upload Odds (CSV)</h2>
          <label className="upload-zone">
            <input type="file" accept=".csv" onChange={handleUpload} disabled={loading} />
            Drop a CSV file here or click to browse
          </label>
          <p style={{ marginTop: 12, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Required columns: sport, league, start_time, home_team, away_team, sportsbook, market, selection, american_odds
          </p>
          {settings?.odds_api_configured && (
            <div className="actions">
              <button className="btn-outline" onClick={handleApiRefresh} disabled={loading}>
                Refresh from Odds API (NBA)
              </button>
            </div>
          )}
          {message && <div className={`message ${messageType}`}>{message}</div>}
        </section>

        <section className="card">
          <h2>Bankroll &amp; Stake Sizing</h2>
          <div className="form-grid">
            <label>
              Bankroll ($)
              <input type="number" value={filters.bankroll} onChange={(e) => updateFilter('bankroll', e.target.value)} />
            </label>
            <label>
              Flat Stake ($)
              <input type="number" value={filters.flat_stake} onChange={(e) => updateFilter('flat_stake', e.target.value)} />
            </label>
            <label>
              Kelly Fraction
              <input type="number" step="0.05" min="0" max="1" value={filters.kelly_fraction} onChange={(e) => updateFilter('kelly_fraction', e.target.value)} disabled={!filters.use_kelly} />
            </label>
          </div>
          <div className="checkbox-row">
            <input type="checkbox" id="kelly" checked={filters.use_kelly} onChange={(e) => updateFilter('use_kelly', e.target.checked)} />
            <label htmlFor="kelly" style={{ flexDirection: 'row', color: 'var(--text)' }}>Use fractional Kelly instead of flat betting</label>
          </div>
        </section>
      </div>

      <section className="card" style={{ marginBottom: 20 }}>
        <h2>Filters</h2>
        <div className="form-grid">
          <label>
            Min EV (%)
            <input type="number" step="0.5" value={filters.min_ev * 100} onChange={(e) => updateFilter('min_ev', Number(e.target.value) / 100)} />
          </label>
          <label>
            Min American Odds
            <input type="number" placeholder="e.g. -200" value={filters.min_odds} onChange={(e) => updateFilter('min_odds', e.target.value)} />
          </label>
          <label>
            Max American Odds
            <input type="number" placeholder="e.g. +500" value={filters.max_odds} onChange={(e) => updateFilter('max_odds', e.target.value)} />
          </label>
          <label>
            Sport
            <select value={filters.sport} onChange={(e) => updateFilter('sport', e.target.value)}>
              <option value="">All sports</option>
              {sports.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          <label>
            Sportsbook
            <select value={filters.sportsbook} onChange={(e) => updateFilter('sportsbook', e.target.value)}>
              <option value="">All books</option>
              {settings?.sportsbooks.map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
          </label>
          <label>
            Market
            <select value={filters.market} onChange={(e) => updateFilter('market', e.target.value)}>
              <option value="">All markets</option>
              {settings?.markets.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </label>
          <label>
            Stale threshold (min)
            <input type="number" value={filters.stale_minutes} onChange={(e) => updateFilter('stale_minutes', e.target.value)} />
          </label>
        </div>
        <div className="actions">
          <button className="btn-primary" onClick={handleScan} disabled={loading}>
            {loading ? 'Scanning…' : 'Scan for +EV Bets'}
          </button>
          <button className="btn-secondary" onClick={handleExport} disabled={!results.length}>
            Export CSV
          </button>
        </div>
      </section>

      <section className="card">
        <h2>+EV Opportunities</h2>
        {scanTime && (
          <div className="stats-row">
            <div className="stat">
              <div className="label">Opportunities</div>
              <div className="value">{results.length}</div>
            </div>
            <div className="stat">
              <div className="label">Last Scan</div>
              <div className="value" style={{ fontSize: '0.9rem' }}>{formatDate(scanTime)}</div>
            </div>
            <div className="stat">
              <div className="label">Min EV Filter</div>
              <div className="value" style={{ fontSize: '1rem' }}>{formatPct(filters.min_ev * 100)}</div>
            </div>
          </div>
        )}

        {results.length === 0 ? (
          <div className="empty-state">
            <h3>No +EV bets found</h3>
            <p>Upload a CSV with odds from multiple Ontario sportsbooks, then scan.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>EV</th>
                  <th>Event</th>
                  <th>Market</th>
                  <th>Selection</th>
                  <th>Book</th>
                  <th>Odds</th>
                  <th>Fair Prob</th>
                  <th>Breakeven</th>
                  <th>Stake</th>
                  <th>Freshness</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={`${r.event_id}-${r.market}-${r.selection}-${r.sportsbook}-${i}`}>
                    <td className="mono ev-positive">{formatPct(r.ev_percent)}</td>
                    <td>
                      <div>{r.away_team} @ {r.home_team}</div>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{r.sport} · {formatDate(r.start_time)}</div>
                    </td>
                    <td>{r.market}{r.line != null ? ` (${r.line > 0 ? '+' : ''}${r.line})` : ''}</td>
                    <td>{r.selection}</td>
                    <td>{r.sportsbook}</td>
                    <td className="mono">{formatOdds(r.american_odds)} <span style={{ color: 'var(--text-muted)' }}>({r.decimal_odds.toFixed(2)})</span></td>
                    <td className="mono">{formatProb(r.fair_probability)}</td>
                    <td className="mono">{formatProb(r.break_even_probability)}</td>
                    <td className="mono">${r.suggested_stake.toFixed(2)} <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>({r.stake_method})</span></td>
                    <td>{r.is_stale ? <span className="stale-flag">STALE</span> : <span className="fresh-flag">FRESH</span>}</td>
                    <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{formatDate(r.last_updated)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <footer className="disclaimer">
        <strong>Disclaimer:</strong> This tool is for informational and educational purposes only.
        It does not place bets, store sportsbook passwords, or bypass any security measures.
        Always verify odds directly on the sportsbook before wagering. Gamble responsibly.
        Ontario sportsbooks: theScore Bet, FanDuel Ontario, DraftKings Ontario, Bet365 Ontario, BetMGM Ontario, Caesars Ontario.
      </footer>
    </div>
  )
}
