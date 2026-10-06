const TONES = {
  Unexplained: 'warn',
  Explained: 'calm',
  'Potentially Undervalued': 'good',
  'Value Trap Risk': 'bad',
  'Overvalued Risk': 'bad',
  'Priced for Quality': 'calm',
}

export default function StatusTag({ value }) {
  const tone = TONES[value] || 'muted'
  return <span className={`tag tag--${tone}`}>{value}</span>
}
