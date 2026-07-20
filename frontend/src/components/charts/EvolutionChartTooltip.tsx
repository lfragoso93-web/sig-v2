import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'

import type {
  ClassEvolutionPoint,
  DailyPoint,
  MonthlyClassEvolutionPoint,
  MonthlyPoint,
} from '@/hooks/useEvolution'
import { formatBRL, formatPercent, signClass } from '@/utils/format'

export type EvolutionTooltipPoint =
  | DailyPoint
  | MonthlyPoint
  | ClassEvolutionPoint
  | MonthlyClassEvolutionPoint

export interface EvolutionTooltipModel {
  sourceLabel: string
  periodReturnLabel: string
  periodReturnPct: number
  priceCoverageLabel: string
  returnQualityLabel: string
}

export function buildEvolutionTooltipModel(
  point: EvolutionTooltipPoint,
  granularity: 'daily' | 'monthly',
): EvolutionTooltipModel {
  const monthlyReturn = 'monthly_return_pct' in point
    ? point.monthly_return_pct
    : null

  return {
    sourceLabel: point.history_source === 'portfolio_class_snapshot'
      ? 'Snapshot da classe'
      : 'Snapshot consolidado',
    periodReturnLabel: granularity === 'monthly' ? 'TWR do mês' : 'TWR do dia',
    periodReturnPct: granularity === 'monthly' && monthlyReturn !== null
      ? monthlyReturn
      : point.daily_return_pct,
    priceCoverageLabel: point.has_partial_prices ? 'Parcial' : 'Completa',
    returnQualityLabel: point.return_is_estimated ? 'Estimado' : 'Calculado',
  }
}

function fullDate(value: string): string {
  try {
    return format(parseISO(value), "dd 'de' MMMM 'de' yyyy", { locale: ptBR })
  } catch {
    return value
  }
}

function MoneyRow({ label, value }: { label: string; value: number }) {
  return (
    <div className={signClass(value)}>
      {label}: <strong>{formatBRL(value)}</strong>
    </div>
  )
}

export default function EvolutionChartTooltip({
  active,
  payload,
  granularity,
}: {
  active?: boolean
  payload?: Array<{ payload: EvolutionTooltipPoint }>
  granularity: 'daily' | 'monthly'
}) {
  const point = payload?.[0]?.payload
  if (!active || !point) return null

  const model = buildEvolutionTooltipModel(point, granularity)

  return (
    <div
      style={{
        minWidth: 240,
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
      <MoneyRow label="Resultado não realizado" value={point.unrealized_pnl} />
      <MoneyRow label="Resultado realizado" value={point.realized_pnl} />
      <div className={signClass(model.periodReturnPct)}>
        {model.periodReturnLabel}: <strong>{model.periodReturnPct >= 0 ? '+' : ''}{formatPercent(model.periodReturnPct)}</strong>
      </div>
      <div className={signClass(point.accumulated_return_pct)}>
        TWR acumulado: <strong>{point.accumulated_return_pct >= 0 ? '+' : ''}{formatPercent(point.accumulated_return_pct)}</strong>
      </div>
      <div style={{ marginTop: 8, color: 'var(--color-text-faint)' }}>
        {model.sourceLabel} · Cobertura {model.priceCoverageLabel} · Retorno {model.returnQualityLabel}
      </div>
    </div>
  )
}
