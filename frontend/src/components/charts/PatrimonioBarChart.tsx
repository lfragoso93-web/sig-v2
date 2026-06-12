import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { formatBRL } from '@/utils/format'

export interface PatrimonioHistoryPoint {
  month: string
  value: number
}

function CustomTooltip({ active, payload, label }: {
  active?: boolean
  payload?: { value: number }[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div
      className="rounded-lg p-3 text-xs"
      style={{
        background:  'var(--color-surface)',
        border:      '1px solid var(--color-border)',
        boxShadow:   'var(--shadow-lg)',
      }}
    >
      <p className="font-semibold mb-2" style={{ color: 'var(--color-text)' }}>{label}</p>
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: 'var(--color-primary)' }} />
        <span style={{ color: 'var(--color-text-muted)' }}>Patrimônio:</span>
        <span className="font-medium" style={{ color: 'var(--color-text)' }}>
          {formatBRL(payload[0].value)}
        </span>
      </div>
    </div>
  )
}

export default function PatrimonioBarChart({ data }: { data: PatrimonioHistoryPoint[] }) {
  if (!data || data.length === 0) return null
  const tickStyle = { fontSize: 10, fill: 'var(--color-text-faint)' }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }} barSize={14}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-divider)" vertical={false} />
        <XAxis dataKey="month" tick={tickStyle} axisLine={false} tickLine={false} />
        <YAxis
          tick={tickStyle}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => formatBRL(v, true)}
          width={60}
        />
        <Tooltip
          content={<CustomTooltip />}
          cursor={{ fill: 'oklch(from var(--color-text) l c h / 0.04)' }}
        />
        <Bar dataKey="value" fill="var(--color-primary)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
