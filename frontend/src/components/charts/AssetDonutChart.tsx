import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import type { AssetTypeDistribution } from '@/hooks/usePortfolio'
import { formatBRL } from '@/utils/format'

// Paleta de cores fixa — usada quando o backend não retornar `color`
const PALETTE = [
  '#01696f', // teal primary
  '#006494', // blue
  '#c18f00', // gold
  '#3d7020', // green
  '#7a39bb', // purple
  '#da7101', // orange
  '#a13544', // notification/rose
  '#4f98a3', // cyan
]

function safeNumber(value: unknown): number {
  const n = Number(value)
  return Number.isFinite(n) ? n : 0
}

function clampPercentage(value: unknown): number {
  const n = safeNumber(value)
  return Math.min(Math.max(n, 0), 100)
}

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
        background: 'var(--color-surface-2)',
        border: '1px solid var(--color-border)',
        boxShadow: 'var(--shadow-lg)',
      }}
    >
      <p className="font-semibold mb-1" style={{ color: 'var(--color-text)' }}>{d.label}</p>
      <p className="tabular-nums font-medium" style={{ color: 'var(--color-text-muted)' }}>
        {formatBRL(safeNumber(d.value))} ({clampPercentage(d.percentage).toFixed(1)}%)
      </p>
    </div>
  )
}

export default function AssetDonutChart({ data }: { data: AssetTypeDistribution[] }) {
  if (!data || data.length === 0) return null

  return (
    <div className="flex flex-col sm:flex-row items-center gap-5 w-full min-w-0">
      {/* Donut */}
      <div style={{ flexShrink: 0, width: 184, height: 184 }}>
        <ResponsiveContainer width={184} height={184}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={54}
              outerRadius={80}
              paddingAngle={2.5}
              dataKey="value"
              stroke="var(--color-surface)"
              strokeWidth={2}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${entry.asset_type ?? index}`} fill={getColor(entry, index)} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Legenda com percentuais seguros */}
      <ul
        aria-label="Legenda de distribuição por classe"
        style={{
          listStyle: 'none',
          margin: 0,
          padding: 0,
          flex: 1,
          width: '100%',
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem',
        }}
      >
        {data.map((entry, index) => {
          const pct = clampPercentage(entry.percentage)
          const color = getColor(entry, index)
          return (
            <li
              key={entry.asset_type}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '0.625rem',
                fontSize: 'var(--text-xs)',
                minWidth: 0,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 0, flex: 1 }}>
                <span
                  aria-hidden="true"
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    background: color,
                    flexShrink: 0,
                  }}
                />
                <span
                  style={{
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    color: 'var(--color-text)',
                    fontWeight: 500,
                  }}
                  title={entry.label}
                >
                  {entry.label}
                </span>
              </div>
              <span
                className="tabular-nums font-semibold"
                style={{
                  color: 'var(--color-text-muted)',
                  flexShrink: 0,
                }}
              >
                {pct.toFixed(1)}%
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
