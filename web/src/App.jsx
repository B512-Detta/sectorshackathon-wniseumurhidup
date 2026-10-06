import { useCallback, useEffect, useMemo, useState } from 'react'
import Masthead from './components/Masthead.jsx'
import Watchlist from './components/Watchlist.jsx'
import StockDetail from './components/StockDetail.jsx'
import { hasValuation } from './format.js'
import { apiUrl } from './api.js'

export default function App() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [onlyUnexplained, setOnlyUnexplained] = useState(false)
  const [onlyValued, setOnlyValued] = useState(false)
  const [selected, setSelected] = useState(null)

  const load = useCallback(async (refresh = false) => {
    setLoading(true)
    setError(null)
    try {
      if (refresh) {
        const r = await fetch(apiUrl('/api/refresh'), { method: 'POST' })
        if (!r.ok) throw new Error()
      }
      const r = await fetch(apiUrl('/api/watchlist'))
      if (!r.ok) throw new Error()
      setData(await r.json())
    } catch {
      setError('Data belum bisa dimuat. Pastikan API jalan di port 8000, lalu coba lagi.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const rows = useMemo(() => {
    if (!data) return []
    return data.rows.filter((r) =>
      (!onlyUnexplained || r.explained === 'Unexplained') &&
      (!onlyValued || hasValuation(r)),
    )
  }, [data, onlyUnexplained, onlyValued])

  const activeTicker = rows.some((r) => r.ticker === selected) ? selected : rows[0]?.ticker

  return (
    <div className="page">
      <Masthead
        data={data}
        loading={loading}
        onRefresh={() => load(true)}
        onlyUnexplained={onlyUnexplained}
        onlyValued={onlyValued}
        setOnlyUnexplained={setOnlyUnexplained}
        setOnlyValued={setOnlyValued}
      />

      {error && <p className="notice notice--error">{error}</p>}
      {data?.errors?.length > 0 && (
        <p className="notice">
          {data.errors.length} saham gagal diambil dari API (kena rate limit, biasanya). Tarik ulang beberapa saat lagi.
        </p>
      )}

      {data && rows.length === 0 && (
        <p className="empty">Tidak ada saham yang cocok. Coba lepas salah satu filternya.</p>
      )}

      {rows.length > 0 && (
        <div className="layout">
          <Watchlist rows={rows} selected={activeTicker} onSelect={setSelected} />
          <StockDetail ticker={activeTicker} />
        </div>
      )}
    </div>
  )
}
