import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { ProventosEvolucao } from '@/services/proventosService'
import { formatBRL } from '@/utils/format'

const COLOR_RECEBIDO  = 'var(--color-primary)'
const COLOR_A_RECEBER = 'oklch(from var(--color-primary) l c h / 0.40)'

function CustomTooltip({ active, payload, label }: {
  active?: boolean
  payload?: { value: number; name: string }[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div
      className="rounded-lg p-3 text-xs"
      style={{
        background:   'var(--color-surface)',
        border:       '1px solid var(--color-border)',
        boxShadow:    'var(--shadow-lg)',
        color:        'var(--color-text)',
      }}
    >
      <p className="font-semibold mb-2" style={{ color: 'var(--color-text)' }}>{label}</p>
      {payload.map(p => (
        <div key={p.name} className="flex items-center gap-2 mb-1">
          <span
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: p.name === 'recebido' ? COLOR_RECEBIDO : COLOR_A_RECEBER }}
          />
          <span style={{ color: 'var(--color-text-muted)' }}>
            {p.name === 'recebido' ? 'Recebidos' : 'A receber'}:
          </span>
          <span className="font-medium" style={{ color: 'var(--color-text)' }}>{formatBRL(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

export default function ProventosBarChart({ data }: { data: ProventosEvolucao[] }) {
  const tickStyle = { fontSize: 10, fill: 'var(--color-text-faint)' }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart
        data={data}
        margin={{ top: 4, right: 4, left: 0, bottom: 0 }}
        barSize={14}
      >
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="var(--color-divider)"
          vertical={false}
        />
        <XAxis
          dataKey="month"
          tick={tickStyle}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={tickStyle}
          axisLine={false}
          tickLine={false}
          tickFormatter={v => formatBRL(v, true)}
          width={58}
        />
        <Tooltip
          content={<CustomTooltip />}
          cursor={{ fill: 'oklch(from var(--color-text) l c h / 0.04)' }}
        />
        <Legend
          verticalAlign="bottom"
          wrapperStyle={{ fontSize: 11, paddingTop: 10, color: 'var(--color-text-muted)' }}
          formatter={v => v === 'recebido' ? 'Recebidos' : 'A receber'}
        />
        <Bar
          dataKey="recebido"
          fill={COLOR_RECEBIDO}
          radius={[3, 3, 0, 0]}
        />
        <Bar
          dataKey="a_receber"
          fill={COLOR_A_RECEBER}
          radius={[3, 3, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  )
}
