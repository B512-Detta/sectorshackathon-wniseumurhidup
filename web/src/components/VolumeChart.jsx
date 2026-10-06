import { compactIdr, shortDate } from '../format.js'

const W = 640
const H = 200
const PAD = { top: 16, right: 12, bottom: 28, left: 56 }

export default function VolumeChart({ series, baseline, highlightLast }) {
  if (!series?.length) return <p className="fine">Belum ada data harian.</p>

  const max = Math.max(...series.map((d) => d.volume || 0), baseline || 0) * 1.08
  const innerW = W - PAD.left - PAD.right
  const innerH = H - PAD.top - PAD.bottom
  const slot = innerW / series.length
  const barW = Math.max(slot * 0.62, 2)
  const y = (v) => PAD.top + innerH - (v / max) * innerH
  const last = series.length - 1

  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Grafik volume harian">
      {[0, 0.5, 1].map((t) => (
        <g key={t}>
          <line x1={PAD.left} x2={W - PAD.right} y1={y(max * t)} y2={y(max * t)} className="chart__grid" />
          <text x={PAD.left - 8} y={y(max * t) + 4} className="chart__axis" textAnchor="end">{compactIdr(max * t)}</text>
        </g>
      ))}
      {baseline != null && (
        <line x1={PAD.left} x2={W - PAD.right} y1={y(baseline)} y2={y(baseline)} className="chart__median" />
      )}
      {series.map((d, i) => {
        const isLast = i === last && highlightLast
        return (
          <rect
            key={d.date}
            x={PAD.left + i * slot + (slot - barW) / 2}
            y={y(d.volume || 0)}
            width={barW}
            height={Math.max(PAD.top + innerH - y(d.volume || 0), 0)}
            className={isLast ? 'bar bar--hot' : 'bar'}
          >
            <title>{`${shortDate(d.date)}: ${compactIdr(d.volume)}`}</title>
          </rect>
        )
      })}
      {[0, Math.floor(last / 2), last].map((i) => (
        <text key={i} x={PAD.left + i * slot + slot / 2} y={H - 8} className="chart__axis" textAnchor="middle">
          {shortDate(series[i].date)}
        </text>
      ))}
    </svg>
  )
}
