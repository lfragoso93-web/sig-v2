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
import { formatBRL, formatPercent, signClass } from '@/utils/format'

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

function fullDate(value: string): string {
  try {
    return format(parseISO(value), "dd 'de' MMMM 'de' yyyy", { locale: ptBR })
  } catch {
    return value
  }
}

function MonthlyTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: Array<{ payload: MonthlyPoint | MonthlyClassEvolutionPoint }>
}) {
  const point = payload?.[0]?.payload
  if (!active || !point) return null

  return (
    <div
      style={{
        minWidth: 220,
        padding: '0.8rem',
        borderRadius: 8,
        border: '1px solid var(--color-border)',
        background: 'var(--color-surface-2)',
        boxShadow: 'var(--shadow-lg)',
        color: 'var(--color-text)',
        fontSize: 'var(--text-xs)',
      }}
    >
      <div style={{ fontWeight: 700, marginBottom: 8 }}>{fullDate(point.date)}</div>
      <div>Patrimônio: <strong>{formatBRL(point.market_value)}</strong></div>
      <div>Custo das posições: <strong>{formatBRL(point.cost_basis)}</strong></div>
      <div className={signClass(point.unrealized_pnl)}>
        Resultado patrimonial: <strong>{formatBRL(point.unrealized_pnl)}</strong>
      </div>
      <div className={signClass(point.net_external_flow)}>
        Fluxo externo no dia: <strong>{formatBRL(point.net_external_flow)}</strong>
      </div>
      <div className={signClass(point.monthly_return_pct)}>
        TWR do mês: <strong>{point.monthly_return_pct >= 0 ? '+' : ''}{formatPercent(point.monthly_return_pct)}</strong>
      </div>
      <div style={{ marginTop: 8, color: 'var(--color-text-faint)' }}>
        Snapshot fechado{point.return_is_estimated ? ' · retorno estimado' : ''}{point.has_partial_prices ? ' · cobertura parcial' : ''}
      </div>
    </div>
  )
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
        <Tooltip content={<MonthlyTooltip />} cursor={{ fill: 'oklch(from var(--color-text) l c h / 0.04)' }} />
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
