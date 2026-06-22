import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'
import type { PatrimonioHistoryPoint } from '@/hooks/usePortfolio'
import { formatBRL } from '@/utils/format'

interface Props {
  data: PatrimonioHistoryPoint[]
  loading?: boolean
  /** Quando verdadeiro, exibe apenas o valor (sem "investido") — útil no modo classe de ativo */
  singleSeries?: boolean
}

const MONTHS = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']

function shortDate(d: string) {
  const [, m, day] = d.split('-')
  if (!m) return d
  const label = MONTHS[parseInt(m, 10) - 1] ?? m
  return day ? `${label}/${day}` : label
}

export default function PatrimonioBarChart({ data, loading, singleSeries }: Props) {
  if (loading) return <div className="skeleton h-64 w-full rounded-xl" />

  if (!data.length) {
    return (
      <div
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 208 }}
      >
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)' }}>
          Sem histórico para o período selecionado
        </p>
      </div>
    )
  }

  const chartData = data.map(d => ({
    name:     shortDate(d.date),
    value:    d.value,
    invested: d.invested ?? 0,
  }))

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tooltipFormatter = (value: any, name: any): [string, string] => {
    const formatted = typeof value === 'number' ? formatBRL(value) : '-'
    const label = name === 'value' ? 'Patrimônio' : 'Investido'
    return [formatted, label]
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={chartData} margin={{ top: 6, right: 4, left: 4, bottom: 0 }}>
        <defs>
          <linearGradient id="gradValue" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="var(--color-primary)" stopOpacity={0.25} />
            <stop offset="100%" stopColor="var(--color-primary)" stopOpacity={0.01} />
          </linearGradient>
          <linearGradient id="gradInvested" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="var(--color-primary)" stopOpacity={0.1} />
            <stop offset="100%" stopColor="var(--color-primary)" stopOpacity={0.01} />
          </linearGradient>
        </defs>

        <CartesianGrid
          strokeDasharray="3 3"
          stroke="oklch(from var(--color-text) l c h / 0.07)"
          vertical={false}
        />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
          axisLine={false} tickLine={false}
        />
        <YAxis
          tickFormatter={(v: number) => formatBRL(v, true)}
          tick={{ fontSize: 9, fill: 'var(--color-text-muted)' }}
          axisLine={false} tickLine={false} width={68}
        />
        <Tooltip
          formatter={tooltipFormatter}
          contentStyle={{
            background: 'var(--color-surface-2)',
            border: '1px solid oklch(from var(--color-text) l c h / 0.1)',
            borderRadius: 8, fontSize: 11,
            color: 'var(--color-text)',
          }}
          cursor={{ stroke: 'var(--color-primary)', strokeWidth: 1, strokeDasharray: '4 2' }}
        />

        <Area
          type="monotone"
          dataKey="value"
          stroke="var(--color-primary)"
          strokeWidth={2}
          fill="url(#gradValue)"
          dot={false}
          activeDot={{ r: 4, fill: 'var(--color-primary)', strokeWidth: 0 }}
        />

        {!singleSeries && (
          <Area
            type="monotone"
            dataKey="invested"
            stroke="oklch(from var(--color-primary) l c h / 0.45)"
            strokeWidth={1.5}
            strokeDasharray="4 3"
            fill="url(#gradInvested)"
            dot={false}
            activeDot={{ r: 3, fill: 'oklch(from var(--color-primary) l c h / 0.7)', strokeWidth: 0 }}
          />
        )}
      </AreaChart>
    </ResponsiveContainer>
  )
}
