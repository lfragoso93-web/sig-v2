import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import EvolutionChartTooltip, {
  buildEvolutionTooltipModel,
  type EvolutionTooltipPoint,
} from './EvolutionChartTooltip'

const classMonthlyPoint: EvolutionTooltipPoint = {
  asset_type: 'ACAO',
  date: '2026-07-18',
  period: '2026-07',
  market_value: 1500,
  cost_basis: 1200,
  realized_pnl: 50,
  unrealized_pnl: 300,
  net_external_flow: 0,
  dividends_day: 10,
  dividends_accumulated: 80,
  daily_return_pct: 0.5,
  monthly_return_pct: 1.75,
  accumulated_return_pct: 12.5,
  has_partial_prices: true,
  return_is_estimated: true,
  valuation_status: 'partial_prices',
  history_source: 'portfolio_class_snapshot',
}

describe('EvolutionChartTooltip', () => {
  it('usa o TWR mensal persistido e expõe a qualidade da classe', () => {
    expect(buildEvolutionTooltipModel(classMonthlyPoint, 'monthly')).toEqual({
      sourceLabel: 'Snapshot da classe',
      periodReturnLabel: 'TWR do mês',
      periodReturnPct: 1.75,
      priceCoverageLabel: 'Parcial',
      returnQualityLabel: 'Estimado',
    })
  })

  it('renderiza patrimônio, custo, resultados, TWR e qualidade', () => {
    render(
      <EvolutionChartTooltip
        active
        granularity="monthly"
        payload={[{ payload: classMonthlyPoint }]}
      />,
    )

    expect(screen.getByText(/Patrimônio:/)).toBeTruthy()
    expect(screen.getByText(/Custo das posições:/)).toBeTruthy()
    expect(screen.getByText(/Resultado não realizado:/)).toBeTruthy()
    expect(screen.getByText(/Resultado realizado:/)).toBeTruthy()
    expect(screen.getByText(/TWR do mês:/)).toBeTruthy()
    expect(screen.getByText(/TWR acumulado:/)).toBeTruthy()
    expect(screen.getByText(/Snapshot da classe · Cobertura Parcial · Retorno Estimado/)).toBeTruthy()
  })
})
