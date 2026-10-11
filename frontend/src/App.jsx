import { useState, useEffect } from 'react'
import {
  fetchOrganizations,
  fetchTransactions,
  fetchLineItems,
  uploadCSV,
  approveMatch,
  rejectMatch,
  ignoreTransaction
} from './api'

function formatMoney(amount) {
  if (amount == null) return '$0.00'
  const num = typeof amount === 'number' ? amount : parseFloat(amount)
  if (isNaN(num)) return '$0.00'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(num)
}

export default function App() {
  const [organizations, setOrganizations] = useState([])
  const [currentOrg, setCurrentOrg] = useState('northwind')
  const [transactions, setTransactions] = useState([])
  const [lineItems, setLineItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [actionLoadingId, setActionLoadingId] = useState(null)
  const [error, setError] = useState(null)

  const [selectedFile, setSelectedFile] = useState(null)
  const [uploadLoading, setUploadLoading] = useState(false)
  const [importSummary, setImportSummary] = useState(null)

  useEffect(() => {
    loadOrganizations()
  }, [])

  useEffect(() => {
    if (currentOrg) {
      loadData(currentOrg)
    }
  }, [currentOrg])

  async function loadOrganizations() {
    try {
      const data = await fetchOrganizations()
      setOrganizations(data)
      if (data.length > 0 && !data.some(o => o.slug === currentOrg)) {
        setCurrentOrg(data[0].slug)
      }
    } catch (err) {
      console.error(err)
    }
  }

  async function loadData(org) {
    setLoading(true)
    setError(null)
    try {
      const [txs, items] = await Promise.all([
        fetchTransactions(org),
        fetchLineItems(org)
      ])
      setTransactions(txs)
      setLineItems(items)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleUpload(e) {
    e.preventDefault()
    if (!selectedFile) return
    setUploadLoading(true)
    setError(null)
    setImportSummary(null)
    try {
      const res = await uploadCSV(selectedFile, currentOrg)
      setImportSummary(res)
      setSelectedFile(null)
      await loadData(currentOrg)
    } catch (err) {
      setError(err.message)
    } finally {
      setUploadLoading(false)
    }
  }

  async function handleApprove(matchId) {
    setActionLoadingId(`approve-${matchId}`)
    setError(null)
    try {
      await approveMatch(matchId, currentOrg)
      await loadData(currentOrg)
    } catch (err) {
      setError(err.message)
    } finally {
      setActionLoadingId(null)
    }
  }

  async function handleReject(matchId) {
    setActionLoadingId(`reject-${matchId}`)
    setError(null)
    try {
      await rejectMatch(matchId, currentOrg)
      await loadData(currentOrg)
    } catch (err) {
      setError(err.message)
    } finally {
      setActionLoadingId(null)
    }
  }

  async function handleIgnore(txId) {
    setActionLoadingId(`ignore-${txId}`)
    setError(null)
    try {
      await ignoreTransaction(txId, currentOrg)
      await loadData(currentOrg)
    } catch (err) {
      setError(err.message)
    } finally {
      setActionLoadingId(null)
    }
  }

  return (
    <div className="container">
      <header className="header">
        <div>
          <h1>ApexReconcile</h1>
          <p className="subtitle">Bank Reconciliation for Capital Calls</p>
        </div>
        <div className="org-switcher">
          <label htmlFor="org-select">Organization:</label>
          <select
            id="org-select"
            value={currentOrg}
            onChange={(e) => {
              setCurrentOrg(e.target.value)
              setImportSummary(null)
            }}
          >
            {organizations.map((org) => (
              <option key={org.slug} value={org.slug}>
                {org.name} ({org.slug})
              </option>
            ))}
          </select>
        </div>
      </header>

      {error && <div className="banner error-banner">{error}</div>}

      <section className="card upload-card">
        <h2>Import Bank Statement CSV</h2>
        <form onSubmit={handleUpload} className="upload-form">
          <input
            type="file"
            accept=".csv"
            onChange={(e) => setSelectedFile(e.target.files[0] || null)}
          />
          <button type="submit" disabled={!selectedFile || uploadLoading}>
            {uploadLoading ? 'Uploading...' : 'Upload CSV'}
          </button>
        </form>

        {importSummary && (
          <div className="summary-box">
            <h3>Import Summary</h3>
            <p>
              Imported: <strong>{importSummary.imported_count}</strong> | Duplicates: <strong>{importSummary.duplicate_count}</strong> | Errors: <strong>{importSummary.errors.length}</strong>
            </p>
            {importSummary.errors.length > 0 && (
              <div className="error-list">
                <h4>Row Errors:</h4>
                <ul>
                  {importSummary.errors.map((err, i) => (
                    <li key={i}>Line {err.line}: {err.message}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>

      <section className="card">
        <h2>Capital Call Line Items</h2>
        {lineItems.length === 0 ? (
          <p className="empty-state">No line items found for this organization.</p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Reference</th>
                  <th>Investor Entity</th>
                  <th>Call #</th>
                  <th>Amount Called</th>
                  <th>Amount Funded</th>
                  <th>Amount Remaining</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {lineItems.map((item) => (
                  <tr key={item.id}>
                    <td><strong>{item.reference}</strong></td>
                    <td>{item.investor_name}</td>
                    <td>#{item.capital_call_number}</td>
                    <td>{formatMoney(item.amount_called)}</td>
                    <td>{formatMoney(item.amount_funded)}</td>
                    <td>{formatMoney(item.amount_remaining)}</td>
                    <td><span className={`badge badge-${item.status}`}>{item.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card">
        <h2>Bank Transactions</h2>
        {loading ? (
          <p className="loading-state">Loading transactions...</p>
        ) : transactions.length === 0 ? (
          <p className="empty-state">No transactions imported yet. Upload a CSV above to begin reconciliation.</p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Description</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Suggested Match</th>
                  <th>Match Reason</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => {
                  const proposedMatches = tx.matches ? tx.matches.filter(m => m.status === 'proposed') : []
                  return (
                    <tr key={tx.id}>
                      <td>{tx.date}</td>
                      <td>
                        <div>{tx.description}</div>
                        <small className="text-muted">Ref: {tx.bank_reference}</small>
                      </td>
                      <td className={tx.type === 'debit' ? 'text-danger' : 'text-success'}>
                        {formatMoney(tx.amount)}
                      </td>
                      <td>
                        <span className={`badge badge-${tx.status}`}>{tx.status}</span>
                      </td>
                      <td>
                        {proposedMatches.length > 0 ? (
                          proposedMatches.map(m => (
                            <div key={m.id} className="match-pill">
                              <strong>{m.line_item_reference}</strong> ({m.investor_name})
                            </div>
                          ))
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                      </td>
                      <td>
                        <div className="reason-text">
                          {tx.review_reason || (proposedMatches[0] ? proposedMatches[0].reason : '—')}
                        </div>
                      </td>
                      <td>
                        <div className="action-buttons">
                          {proposedMatches.map(m => (
                            <span key={m.id} className="match-actions">
                              <button
                                className="btn btn-sm btn-success"
                                disabled={actionLoadingId != null}
                                onClick={() => handleApprove(m.id)}
                              >
                                {actionLoadingId === `approve-${m.id}` ? 'Approving...' : `Approve ${m.line_item_reference}`}
                              </button>
                              <button
                                className="btn btn-sm btn-outline-danger"
                                disabled={actionLoadingId != null}
                                onClick={() => handleReject(m.id)}
                              >
                                {actionLoadingId === `reject-${m.id}` ? 'Rejecting...' : 'Reject'}
                              </button>
                            </span>
                          ))}
                          {tx.status !== 'reconciled' && tx.status !== 'ignored' && (
                            <button
                              className="btn btn-sm btn-secondary"
                              disabled={actionLoadingId != null}
                              onClick={() => handleIgnore(tx.id)}
                            >
                              {actionLoadingId === `ignore-${tx.id}` ? 'Ignoring...' : 'Ignore'}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
