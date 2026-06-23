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

function tooltipLabelFormatter(label: string): string {
  try {
    return format(parseISO(label), "dd 'de' MMMM yyyy", { locale: ptBR })
  } catch {
    return label
  }
}

// Subsampla para no maximo maxPoints para evitar render pesado
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
        Sem dados de evolucao para o periodo selecionado.
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={display} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="gradMarket" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="var(--color-primary)" stopOpacity={0.18} />
            <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="gradInvested" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="var(--color-text-muted)" stopOpacity={0.10} />
            <stop offset="95%" stopColor="var(--color-text-muted)" stopOpacity={0} />
          </linearGradient>
        </defs>
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
          labelFormatter={tooltipLabelFormatter}
          formatter={(value: number, name: string) => [
            formatBRL(value),
            name === 'market_value' ? 'Valor de mercado' : 'Custo / investido',
          ]}
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
          formatter={name => name === 'market_value' ? 'Valor de mercado' : 'Custo / investido'}
          wrapperStyle={{ fontSize: 12, paddingTop: 8, color: 'var(--color-text-muted)' }}
        />
        <Area
          type="monotone"
          dataKey="invested_total"
          stroke="var(--color-text-muted)"
          strokeWidth={1.5}
          strokeDasharray="4 3"
          fill="url(#gradInvested)"
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
