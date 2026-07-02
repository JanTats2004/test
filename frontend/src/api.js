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

export async function refreshOddsAPI(sportKey) {
  const res = await fetch(`${API_BASE}/api/odds-api/refresh/${sportKey}`, { method: 'POST' })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'API refresh failed')
  }
  return res.json()
}
