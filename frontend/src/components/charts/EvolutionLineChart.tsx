import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import type { DailyPoint } from '@/hooks/useEvolution'
import { formatBRL } from '@/utils/format'

interface Props {
  data: DailyPoint[]
}

function xTickFormatter(value: string): string {
  try {
    return format(parseISO(value), 'dd/MM', { locale: ptBR })
  } catch {
    return value
  }
}

function tooltipLabelFormatter(label: unknown): string {
  const str = typeof label === 'string' ? label : String(label ?? '')
  try {
    return format(parseISO(str), "dd 'de' MMMM yyyy", { locale: ptBR })
  } catch {
    return str
  }
}

function tooltipFormatter(value: unknown, name: unknown): [string, string] {
  const num = typeof value === 'number' ? value : Number(value ?? 0)
  const key = String(name ?? '')
  return [
    formatBRL(num),
    key === 'market_value' ? 'Patrimônio no fechamento' : 'Custo das posições abertas',
  ]
}

function subsample<T>(arr: T[], maxPoints: number): T[] {
  if (arr.length <= maxPoints) return arr
  const step = Math.ceil(arr.length / maxPoints)
  return arr.filter((_, i) => i % step === 0 || i === arr.length - 1)
}

export default function EvolutionLineChart({ data }: Props) {
  const display = subsample(data, 180)

  if (!display.length) {
    return (
      <div className="flex items-center justify-center h-64 text-sm" style={{ color: 'var(--color-text-muted)' }}>
        Sem dados de evolução para o período selecionado.
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={display} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="gradMarket" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.18} />
            <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="gradCost" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--color-text-muted)" stopOpacity={0.10} />
            <stop offset="95%" stopColor="var(--color-text-muted)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-divider)" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={xTickFormatter}
          tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
          axisLine={false}
          tickLine={false}
          minTickGap={40}
        />
        <YAxis
          tickFormatter={v => formatBRL(v as number).replace('R$\u00a0', '')}
          tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
          axisLine={false}
          tickLine={false}
          width={68}
        />
        <Tooltip
          labelFormatter={tooltipLabelFormatter as never}
          formatter={tooltipFormatter as never}
          contentStyle={{
            background: 'var(--color-surface-2)',
            border: '1px solid var(--color-border)',
            borderRadius: 8,
            fontSize: 12,
            color: 'var(--color-text)',
          }}
          itemStyle={{ color: 'var(--color-text)' }}
          labelStyle={{ fontWeight: 600, marginBottom: 4, color: 'var(--color-text-muted)' }}
        />
        <Legend
          iconType="circle"
          iconSize={8}
          formatter={name => name === 'market_value' ? 'Patrimônio no fechamento' : 'Custo das posições abertas'}
          wrapperStyle={{ fontSize: 12, paddingTop: 8, color: 'var(--color-text-muted)' }}
        />
        <Area
          type="monotone"
          dataKey="cost_basis"
          stroke="var(--color-text-muted)"
          strokeWidth={1.5}
          strokeDasharray="4 3"
          fill="url(#gradCost)"
          dot={false}
          activeDot={{ r: 3 }}
        />
        <Area
          type="monotone"
          dataKey="market_value"
          stroke="var(--color-primary)"
          strokeWidth={2}
          fill="url(#gradMarket)"
          dot={false}
          activeDot={{ r: 4, strokeWidth: 0 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
