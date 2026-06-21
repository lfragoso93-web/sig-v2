import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import type { AssetTypeDistribution } from '@/hooks/usePortfolio'

// Paleta de cores fixa — usada quando o backend não retornar `color`
const PALETTE = [
  '#6366f1', // indigo
  '#10b981', // emerald
  '#f59e0b', // amber
  '#3b82f6', // blue
  '#ec4899', // pink
  '#8b5cf6', // violet
  '#14b8a6', // teal
  '#f97316', // orange
]

function getColor(entry: AssetTypeDistribution, index: number): string {
  return entry.color && entry.color !== '#000000' && entry.color !== 'black'
    ? entry.color
    : PALETTE[index % PALETTE.length]
}

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
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        boxShadow: 'var(--shadow-lg)',
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
    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
      {/* Donut */}
      <div style={{ flexShrink: 0 }}>
        <ResponsiveContainer width={180} height={180}>
          <PieChart>
            <Pie
              data={data}
              cx="50%" cy="50%"
              innerRadius={50}
              outerRadius={78}
              paddingAngle={3}
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getColor(entry, index)} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Legenda com % */}
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, flex: 1, minWidth: 0 }}>
        {data.map((entry, index) => (
          <li
            key={entry.asset_type}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              marginBottom: 6,
              fontSize: 12,
            }}
          >
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                background: getColor(entry, index),
                flexShrink: 0,
              }}
            />
            <span
              style={{
                flex: 1,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                color: 'var(--color-text)',
              }}
            >
              {entry.label}
            </span>
            <span style={{ color: 'var(--color-text-muted)', fontVariantNumeric: 'tabular-nums' }}>
              {entry.percentage.toFixed(1)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
