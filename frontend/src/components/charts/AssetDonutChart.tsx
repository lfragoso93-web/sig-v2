import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import type { AssetTypeDistribution } from '@/hooks/usePortfolio'

function CustomTooltip({ active, payload }: {
  active?: boolean
  payload?: { payload: AssetTypeDistribution }[]
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
      <p className="font-semibold mb-1" style={{ color: 'var(--color-text)' }}>{d.label}</p>
      <p style={{ color: 'var(--color-text-muted)' }}>{d.percentage.toFixed(1)}%</p>
    </div>
  )
}

export default function AssetDonutChart({ data }: { data: AssetTypeDistribution[] }) {
  if (!data || data.length === 0) return null
  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie
          data={data}
          cx="50%" cy="50%"
          innerRadius={55}
          outerRadius={80}
          paddingAngle={3}
          dataKey="value"
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
      </PieChart>
    </ResponsiveContainer>
  )
}
