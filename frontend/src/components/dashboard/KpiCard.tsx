interface Props {
  label: string
  value: string
  change: string
  positive: boolean | null  // null = neutro
}

export default function KpiCard({ label, value, change, positive }: Props) {
  const changeClass =
    positive === null
      ? 'text-[var(--color-text-muted)]'
      : positive
      ? 'kpi-change positive'
      : 'kpi-change negative'

  return (
    <div className="kpi-card">
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value}</span>
      <span className={`text-xs font-medium ${changeClass}`}>{change}</span>
    </div>
  )
}
