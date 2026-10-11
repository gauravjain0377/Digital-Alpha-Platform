const API_BASE = 'http://127.0.0.1:8000/api'

export async function fetchOrganizations() {
  const res = await fetch(`${API_BASE}/organizations/`)
  if (!res.ok) throw new Error('Failed to fetch organizations')
  return res.json()
}

export async function fetchTransactions(org) {
  const res = await fetch(`${API_BASE}/transactions/`, {
    headers: { 'X-Organization': org }
  })
  if (!res.ok) throw new Error('Failed to fetch transactions')
  return res.json()
}

export async function fetchLineItems(org) {
  const res = await fetch(`${API_BASE}/line-items/`, {
    headers: { 'X-Organization': org }
  })
  if (!res.ok) throw new Error('Failed to fetch line items')
  return res.json()
}

export async function uploadCSV(file, org) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/import/`, {
    method: 'POST',
    headers: { 'X-Organization': org },
    body: formData
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || 'Failed to upload CSV')
  return data
}

export async function approveMatch(matchId, org) {
  const res = await fetch(`${API_BASE}/matches/${matchId}/approve/`, {
    method: 'POST',
    headers: { 'X-Organization': org }
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || 'Failed to approve match')
  return data
}

export async function rejectMatch(matchId, org) {
  const res = await fetch(`${API_BASE}/matches/${matchId}/reject/`, {
    method: 'POST',
    headers: { 'X-Organization': org }
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || 'Failed to reject match')
  return data
}

export async function ignoreTransaction(txId, org) {
  const res = await fetch(`${API_BASE}/transactions/${txId}/ignore/`, {
    method: 'POST',
    headers: { 'X-Organization': org }
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.error || 'Failed to ignore transaction')
  return data
}
