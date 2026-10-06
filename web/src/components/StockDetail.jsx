import { useEffect, useState } from 'react'
import { cleanName, compactIdr, multiple, num, pct } from '../format.js'
import StatusTag from './StatusTag.jsx'
import VolumeChart from './VolumeChart.jsx'
import { apiUrl } from '../api.js'

export default function StockDetail({ ticker }) {
  const [state, setState] = useState({ status: 'idle', data: null })

  useEffect(() => {
    if (!ticker) return
    const ctrl = new AbortController()
    setState({ status: 'loading', data: null })
    fetch(apiUrl(`/api/stocks/${ticker}`), { signal: ctrl.signal })
      .then((r) => { if (!r.ok) throw new Error(); return r.json() })
      .then((data) => setState({ status: 'ready', data }))
      .catch((e) => { if (e.name !== 'AbortError') setState({ status: 'error', data: null }) })
    return () => ctrl.abort()
  }, [ticker])

  if (!ticker) return <aside className="detail detail--empty">Pilih satu saham di kiri buat lihat detailnya.</aside>
  if (state.status === 'error') return <aside className="detail">Detail {ticker} gagal dimuat. Coba pilih ulang.</aside>
  if (state.status !== 'ready') return <aside className="detail detail--loading" aria-busy="true">Mengambil detail {ticker.replace('.JK', '')}…</aside>

  const { row, volume_series, volume_baseline, narrative, narrative_source } = state.data
  const unexplained = row.explained === 'Unexplained'
  const hasVal = !['Belum dicek', 'Data peer tidak cukup'].includes(row.gap_label)

  return (
    <aside className="detail">
      <header className="detail__head">
        <p className="kicker">{row.subsector !== '-' ? row.subsector.replace(/-/g, ' ') : 'Tanpa subsector'}</p>
        <h2>{row.ticker.replace('.JK', '')}</h2>
        <p className="detail__name">{cleanName(row.name)}</p>
        <div className="tags">
          <StatusTag value={row.explained} />
          {hasVal && <StatusTag value={row.gap_label} />}
        </div>
      </header>

      <dl className="stats">
        <div><dt>Volume vs median 20h</dt><dd>{multiple(row.volume_ratio)}</dd></div>
        <div><dt>Modified z</dt><dd>{num(row.volume_z, 1)}</dd></div>
        <div><dt>Return 1 hari</dt><dd>{pct(row.ret_1d)}</dd></div>
        <div><dt>Selisih vs peer</dt><dd>{row.divergence_pct == null ? '–' : `${row.divergence_pct >= 0 ? '+' : ''}${row.divergence_pct.toFixed(1)} pp`}</dd></div>
        <div><dt>Volume hari ini</dt><dd>{compactIdr(row.volume)}</dd></div>
        <div><dt>Close</dt><dd>{num(row.close)}</dd></div>
      </dl>

      <section className="block">
        <h3>Volume 21 hari terakhir</h3>
        <p className="fine">Garis putus-putus = median 20 hari sebelumnya. Batang oranye = hari anomali.</p>
        <VolumeChart series={volume_series} baseline={volume_baseline} highlightLast={row.is_anomaly} />
      </section>

      {hasVal && (
        <section className="block">
          <h3>Valuasi vs peer</h3>
          <dl className="stats stats--tight">
            <div><dt>P/E</dt><dd>{row.pe == null || row.pe > 100 ? 'n/m' : multiple(row.pe)}</dd></div>
            <div><dt>P/BV</dt><dd>{multiple(row.pb, 2)}</dd></div>
            <div><dt>ROE</dt><dd>{row.roe == null ? '–' : `${(row.roe * 100).toFixed(1)}%`}</dd></div>
            <div><dt>ROE median peer</dt><dd>{row.peer_roe_median == null ? '–' : `${(row.peer_roe_median * 100).toFixed(1)}%`}</dd></div>
          </dl>
          <p className="fine">Dihitung dari {row.peer_count} peer di rentang market cap 5x.</p>
        </section>
      )}

      <section className="block">
        <h3>Narasi</h3>
        <blockquote className={`narr ${unexplained ? 'narr--warn' : ''}`}>
          {narrative}
          <footer>Sumber: {narrative_source === 'gemini' ? 'Gemini' : 'template, hanya angka'}</footer>
        </blockquote>
      </section>
    </aside>
  )
}
