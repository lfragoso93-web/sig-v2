import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import type { PatrimonioHistoryPoint } from '@/hooks/usePortfolio'
import { formatBRL } from '@/utils/format'

interface Props {
  data: PatrimonioHistoryPoint[]
  loading?: boolean
}

function shortDate(d: string) {
  const parts = d.split('-')
  if (parts.length >= 2) {
    const months = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
    const m = parseInt(parts[1], 10) - 1
    return months[m] ?? d
  }
  return d
}

export default function PatrimonioBarChart({ data, loading }: Props) {
  if (loading) {
    return <div className="skeleton h-64 w-full rounded-xl" />
  }

  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-48" style={{ color: 'var(--color-text-faint)' }}>
        <p className="text-sm">Sem histórico de patrimônio</p>
      </div>
    )
  }

  const chartData = data.map(d => ({
    name:     shortDate(d.date),
    value:    d.value,
    invested: d.invested ?? 0,
  }))

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={chartData} margin={{ top: 4, right: 8, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-divider)" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
          axisLine={false} tickLine={false}
        />
        <YAxis
          tickFormatter={(v: number) => formatBRL(v, true)}
          tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
          axisLine={false} tickLine={false} width={72}
        />
        <Tooltip
          formatter={(value: number, name: string) => [
            formatBRL(value),
            name === 'value' ? 'Patrimônio' : 'Investido',
          ]}
          contentStyle={{
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Legend
          formatter={(v: string) => (
            <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
              {v === 'value' ? 'Patrimônio' : 'Investido'}
            </span>
          )}
        />
        <Bar dataKey="value"    fill="var(--color-primary)" radius={[4,4,0,0]} maxBarSize={40} />
        <Bar dataKey="invested" fill="var(--color-teal)"    radius={[4,4,0,0]} maxBarSize={40} opacity={0.6} />
      </BarChart>
    </ResponsiveContainer>
  )
}
