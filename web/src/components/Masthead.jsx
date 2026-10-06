import { shortDate } from '../format.js'

export default function Masthead({ data, loading, onRefresh, onlyUnexplained, onlyValued, setOnlyUnexplained, setOnlyValued }) {
  return (
    <header className="masthead">
      <div className="masthead__top">
        <p className="kicker">Watchlist anomali harian IDX</p>
        <button className="btn" onClick={onRefresh} disabled={loading}>
          {loading ? 'Lagi narik data…' : 'Tarik ulang'}
        </button>
      </div>
      <h1>Anomali IDX <span className="amp">+</span> Valuation Gap</h1>
      {data && (
        <p className="meta">
          Data per <b>{data.as_of ? shortDate(data.as_of) : 'belum ada'}</b>
          <span className="dot" />
          universe <b>{data.universe_size}</b> saham
          <span className="dot" />
          lolos likuiditas <b>{data.rows.length}</b>
          <span className="dot" />
          dilewati corporate action <b>{data.skipped.length}</b>
        </p>
      )}
      <div className="filters" role="group" aria-label="Filter watchlist">
        <label className="chip">
          <input type="checkbox" checked={onlyUnexplained} onChange={(e) => setOnlyUnexplained(e.target.checked)} />
          Cuma yang belum ada penjelasan
        </label>
        <label className="chip">
          <input type="checkbox" checked={onlyValued} onChange={(e) => setOnlyValued(e.target.checked)} />
          Cuma yang punya label valuasi
        </label>
      </div>
    </header>
  )
}
