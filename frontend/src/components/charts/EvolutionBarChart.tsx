import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell,
} from 'recharts'
import type { ValueType, NameType } from 'recharts/types/component/DefaultTooltipContent'
import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import type { MonthlyPoint } from '@/hooks/useEvolution'
import { formatBRL, formatPercent } from '@/utils/format'

interface Props {
  data: MonthlyPoint[]
}

function xTickFormatter(value: string): string {
  try {
    return format(parseISO(value), "MMM'/'yy", { locale: ptBR })
  } catch {
    return value
  }
}

function tooltipLabelFormatter(label: unknown): string {
  const str = typeof label === 'string' ? label : String(label ?? '')
  try {
    return format(parseISO(str), "MMMM 'de' yyyy", { locale: ptBR })
  } catch {
    return str
  }
}

function tooltipFormatter(
  value: ValueType,
  name: NameType,
): [string, string] {
  const num = typeof value === 'number' ? value : Number(value ?? 0)
  const key = String(name)
  if (key === 'return_pct') return [formatPercent(num), 'Rentabilidade']
  return [
    formatBRL(num),
    key === 'value' ? 'Valor de mercado' : 'Investido',
  ]
}

export default function EvolutionBarChart({ data }: Props) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-sm" style={{ color: 'var(--color-text-muted)' }}>
        Sem dados mensais para o periodo selecionado.
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="var(--color-divider)"
          vertical={false}
        />
        <XAxis
          dataKey="date"
          tickFormatter={xTickFormatter}
          tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
          axisLine={false}
          tickLine={false}
          minTickGap={20}
        />
        <YAxis
          tickFormatter={v => formatBRL(v as number).replace('R$\u00a0', '')}
          tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
          axisLine={false}
          tickLine={false}
          width={68}
        />
        <Tooltip
          labelFormatter={tooltipLabelFormatter}
          formatter={tooltipFormatter}
          contentStyle={{
            background:   'var(--color-surface-2)',
            border:       '1px solid var(--color-border)',
            borderRadius: 8,
            fontSize:     12,
            color:        'var(--color-text)',
          }}
          itemStyle={{ color: 'var(--color-text)' }}
          labelStyle={{ fontWeight: 600, marginBottom: 4, color: 'var(--color-text-muted)' }}
        />
        <Legend
          iconType="circle"
          iconSize={8}
          formatter={name =>
            name === 'value' ? 'Valor de mercado' : 'Investido'
          }
          wrapperStyle={{ fontSize: 12, paddingTop: 8, color: 'var(--color-text-muted)' }}
        />
        <Bar dataKey="invested" fill="var(--color-surface-dynamic)" radius={[3, 3, 0, 0]}>
          {data.map((_, i) => (
            <Cell
              key={i}
              fill="oklch(from var(--color-text-muted) l c h / 0.25)"
            />
          ))}
        </Bar>
        <Bar dataKey="value" radius={[3, 3, 0, 0]}>
          {data.map((d, i) => (
            <Cell
              key={i}
              fill={
                d.value >= d.invested
                  ? 'var(--color-primary)'
                  : 'var(--color-notification)'
              }
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
