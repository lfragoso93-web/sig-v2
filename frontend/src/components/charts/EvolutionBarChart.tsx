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
import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import type { MonthlyClassEvolutionPoint, MonthlyPoint } from '@/hooks/useEvolution'
import { formatBRL } from '@/utils/format'
import EvolutionChartTooltip from './EvolutionChartTooltip'

interface Props {
  data: Array<MonthlyPoint | MonthlyClassEvolutionPoint>
}

function xTickFormatter(value: string): string {
  try {
    return format(parseISO(value), "MMM'/'yy", { locale: ptBR })
  } catch {
    return value
  }
}

export default function EvolutionBarChart({ data }: Props) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-64 text-sm" style={{ color: 'var(--color-text-muted)' }}>
        Sem dados mensais para o período selecionado.
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-divider)" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={xTickFormatter}
          tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
          axisLine={false}
          tickLine={false}
          minTickGap={20}
        />
        <YAxis
          tickFormatter={value => formatBRL(value as number).replace('R$\u00a0', '')}
          tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
          axisLine={false}
          tickLine={false}
          width={68}
        />
        <Tooltip content={<EvolutionChartTooltip granularity="monthly" />} cursor={{ fill: 'oklch(from var(--color-text) l c h / 0.04)' }} />
        <Legend
          iconType="circle"
          iconSize={8}
          formatter={name => name === 'market_value' ? 'Patrimônio no fechamento' : 'Custo das posições abertas'}
          wrapperStyle={{ fontSize: 12, paddingTop: 8, color: 'var(--color-text-muted)' }}
        />
        <Bar dataKey="cost_basis" radius={[3, 3, 0, 0]}>
          {data.map((_, index) => (
            <Cell key={index} fill="oklch(from var(--color-text-muted) l c h / 0.25)" />
          ))}
        </Bar>
        <Bar dataKey="market_value" radius={[3, 3, 0, 0]}>
          {data.map((point, index) => (
            <Cell
              key={index}
              fill={point.market_value >= point.cost_basis ? 'var(--color-primary)' : 'var(--color-notification)'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
