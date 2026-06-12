import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import { ProventoDistribution } from '@/services/proventosService'
import { formatBRL } from '@/utils/format'

const PALETTE = [
  'var(--color-primary)',
  '#22c55e','#f97316','#a78bfa','#f43f5e',
  '#2dd4bf','#fbbf24','#94a3b8','#ec4899','#10b981',
]

function CustomTooltip({ active, payload }: {
  active?: boolean
  payload?: { payload: ProventoDistribution }[]
}) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div
      className="rounded-lg p-3 text-xs"
      style={{
        background:  'var(--color-surface)',
        border:      '1px solid var(--color-border)',
        boxShadow:   'var(--shadow-lg)',
      }}
    >
      <p className="font-semibold mb-1" style={{ color: 'var(--color-text)' }}>{d.ticker}</p>
      <p style={{ color: 'var(--color-text-muted)' }}>
        {formatBRL(d.total)}
        <span className="ml-1" style={{ color: 'var(--color-text)' }}>({d.percentage.toFixed(2)}%)</span>
      </p>
    </div>
  )
}

export default function ProventosDonutChart({ data }: { data: ProventoDistribution[] }) {
  const top = data.slice(0, 10)
  return (
    <div className="flex flex-col gap-3">
      <ResponsiveContainer width="100%" height={160}>
        <PieChart>
          <Pie
            data={top}
            dataKey="total"
            nameKey="ticker"
            cx="50%" cy="50%"
            innerRadius={45}
            outerRadius={70}
            paddingAngle={2}
          >
            {top.map((entry, i) => (
              <Cell key={entry.ticker} fill={PALETTE[i % PALETTE.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>

      {/* Legenda manual com CSS vars */}
      <div className="flex flex-col gap-1.5">
        {top.map((entry, i) => (
          <div key={entry.ticker} className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: PALETTE[i % PALETTE.length] }}
              />
              <span style={{ color: 'var(--color-text-muted)' }}>{entry.ticker}</span>
            </div>
            <span className="font-medium tabular-nums" style={{ color: 'var(--color-text)' }}>
              {entry.percentage.toFixed(2)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
