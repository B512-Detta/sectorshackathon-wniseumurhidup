import { multiple, pct, num, cleanName } from '../format.js'
import StatusTag from './StatusTag.jsx'

export default function Watchlist({ rows, selected, onSelect }) {
  return (
    <section className="ledger" aria-label="Daftar anomali">
      <div className="ledger__head">
        <span>Saham</span>
        <span className="right">Volume</span>
        <span className="right">Return</span>
        <span className="right">Skor</span>
        <span>Status</span>
      </div>
      <ol className="ledger__rows">
        {rows.map((r, i) => (
          <li key={r.ticker}>
            <button
              className={`ledger__row ${selected === r.ticker ? 'is-active' : ''}`}
              onClick={() => onSelect(r.ticker)}
              aria-pressed={selected === r.ticker}
            >
              <span className="ledger__name">
                <span className="rank">{String(i + 1).padStart(2, '0')}</span>
                <span>
                  <span className="ticker">{r.ticker.replace('.JK', '')}</span>
                  <span className="company">{cleanName(r.name)}</span>
                </span>
              </span>
              <span className="right mono">{multiple(r.volume_ratio)}</span>
              <span className={`right mono ${r.ret_1d < 0 ? 'neg' : r.ret_1d > 0 ? 'pos' : ''}`}>{pct(r.ret_1d)}</span>
              <span className="right mono">
                <span className="score"><span style={{ width: `${Math.min(r.composite, 100)}%` }} /></span>
                {num(r.composite)}
              </span>
              <span><StatusTag value={r.explained} /></span>
            </button>
          </li>
        ))}
      </ol>
    </section>
  )
}
