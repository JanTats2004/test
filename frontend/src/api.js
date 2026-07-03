const API_BASE = import.meta.env.VITE_API_URL || ''

export async function fetchSettings() {
  const res = await fetch(`${API_BASE}/api/settings`)
  if (!res.ok) throw new Error('Failed to load settings')
  return res.json()
}

export async function uploadCSV(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/api/import/csv`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) throw new Error('CSV upload failed')
  return res.json()
}

export async function scanEV(params) {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      query.set(key, String(value))
    }
  })
  const res = await fetch(`${API_BASE}/api/ev/scan?${query}`)
  if (!res.ok) throw new Error('EV scan failed')
  return res.json()
}

export function exportEVUrl(params) {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      query.set(key, String(value))
    }
  })
  return `${API_BASE}/api/ev/export?${query}`
}

export async function fetchOddsAPISports() {
  const res = await fetch(`${API_BASE}/api/odds-api/sports`)
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to load sports')
  }
  return res.json()
}

export async function fetchOddsFromAPI({ sport_key, regions, markets }) {
  const res = await fetch(`${API_BASE}/api/odds-api/fetch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sport_key, regions, markets }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to fetch odds')
  }
  return res.json()
}

export async function previewOddsFromAPI({ sport_key, regions, markets }) {
  const query = new URLSearchParams({ sport_key, regions, markets })
  const res = await fetch(`${API_BASE}/api/odds-api/preview?${query}`)
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to preview odds')
  }
  return res.json()
}

export async function listOdds(params = {}) {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value) query.set(key, value)
  })
  const res = await fetch(`${API_BASE}/api/odds?${query}`)
  if (!res.ok) throw new Error('Failed to load odds')
  return res.json()
}

export async function refreshOddsAPI(sportKey, regions = 'us', markets = 'moneyline,spread,totals') {
  const query = new URLSearchParams({ regions, markets })
  const res = await fetch(`${API_BASE}/api/odds-api/refresh/${sportKey}?${query}`, { method: 'POST' })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'API refresh failed')
  }
  return res.json()
}
