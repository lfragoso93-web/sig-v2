import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'
import { formatBRL } from '@/utils/format'
import type { PatrimonioHistoryPoint } from '@/hooks/usePortfolio'

// Tooltip customizado com 3 linhas: Patrimônio, Investido, Ganho/Perda
function CustomTooltip({ active, payload, label }: {
  active?: boolean
  payload?: Array<{ name: string; value: number; color: string }>[]
  label?: string
}) {
  if (!active || !payload?.length) return null

  const byName: Record<string, number> = {}
  ;(payload as any[]).forEach((p: any) => { byName[p.name] = p.value })

  const patrimonio = byName['value']    ?? 0
  const investido  = byName['invested'] ?? 0
  const diff       = patrimonio - investido
  const isGain     = diff >= 0

  return (
    <div
      className="rounded-lg p-3 text-xs min-w-[180px]"
      style={{
        background: 'var(--color-surface)',
        border:     '1px solid var(--color-border)',
        boxShadow:  'var(--shadow-lg)',
      }}
    >
      <p className="font-semibold mb-2" style={{ color: 'var(--color-text)' }}>{label}</p>

      <div className="flex items-center justify-between gap-4 mb-1">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ background: 'var(--color-primary)' }} />
          <span style={{ color: 'var(--color-text-muted)' }}>Patrimônio</span>
        </div>
        <span className="font-semibold tabular-nums" style={{ color: 'var(--color-text)' }}>
          {formatBRL(patrimonio)}
        </span>
      </div>

      <div className="flex items-center justify-between gap-4 mb-1">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ background: 'oklch(from var(--color-primary) l c h / 0.45)' }} />
          <span style={{ color: 'var(--color-text-muted)' }}>Investido</span>
        </div>
        <span className="font-medium tabular-nums" style={{ color: 'var(--color-text-muted)' }}>
          {formatBRL(investido)}
        </span>
      </div>

      <div
        className="flex items-center justify-between gap-4 mt-2 pt-2"
        style={{ borderTop: '1px solid var(--color-divider)' }}
      >
        <span style={{ color: 'var(--color-text-faint)' }}>
          {isGain ? 'Ganho' : 'Perda'}
        </span>
        <span
          className="font-semibold tabular-nums"
          style={{ color: isGain ? 'var(--color-success)' : 'var(--color-notification)' }}
        >
          {isGain ? '+' : ''}{formatBRL(diff)}
        </span>
      </div>
    </div>
  )
}

export default function PatrimonioBarChart({ data }: { data: PatrimonioHistoryPoint[] }) {
  if (!data || data.length === 0) return null

  const tickStyle = { fontSize: 10, fill: 'var(--color-text-faint)' }

  const barData = data.map(d => ({
    ...d,
    _gain: d.value >= d.invested,
  }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <ComposedChart data={barData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }} barSize={14}>
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

        <Bar
          dataKey="value"
          name="value"
          radius={[4, 4, 0, 0]}
          fill="var(--color-primary)"
        >
          {barData.map((_entry, index) => (
            <rect key={`cell-${index}`} />
          ))}
        </Bar>

        <Line
          type="monotone"
          dataKey="invested"
          name="invested"
          stroke="oklch(from var(--color-primary) l c h / 0.40)"
          strokeWidth={2}
          strokeDasharray="4 3"
          dot={false}
          activeDot={{ r: 4, fill: 'oklch(from var(--color-primary) l c h / 0.40)' }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
