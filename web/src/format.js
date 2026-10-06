export const pct = (v, digits = 1) =>
  v == null ? '–' : `${v >= 0 ? '+' : ''}${(v * 100).toFixed(digits)}%`

export const multiple = (v, digits = 1) =>
  v == null ? '–' : `${v.toLocaleString('id-ID', { minimumFractionDigits: digits, maximumFractionDigits: digits })}x`

export const num = (v, digits = 0) => (v == null ? '–' : v.toFixed(digits))

export const compactIdr = (v) => {
  if (v == null) return '–'
  if (v >= 1e12) return `${(v / 1e12).toFixed(1)} T`
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)} M`
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)} jt`
  return v.toLocaleString('id-ID')
}

export const shortDate = (iso) =>
  new Date(iso + 'T00:00:00').toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })

export const cleanName = (name) => (name || '').replace(/^PT\s+/, '').replace(/\s+Tbk\.?$/i, '')

export const VALUATION_PLACEHOLDERS = ['Belum dicek', 'Data peer tidak cukup']
export const hasValuation = (row) => !VALUATION_PLACEHOLDERS.includes(row.gap_label)
