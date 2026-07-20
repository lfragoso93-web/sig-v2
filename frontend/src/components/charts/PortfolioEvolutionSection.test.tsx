import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  useClassDailyEvolution,
  useClassMonthlyEvolution,
  useClassTwrAvailability,
  useDailyEvolution,
  useMonthlyEvolution,
} from '@/hooks/useEvolution'
import PortfolioEvolutionSection from './PortfolioEvolutionSection'

vi.mock('@/hooks/useEvolution', () => ({
  useClassDailyEvolution: vi.fn(),
  useClassMonthlyEvolution: vi.fn(),
  useClassTwrAvailability: vi.fn(),
  useDailyEvolution: vi.fn(),
  useMonthlyEvolution: vi.fn(),
}))

function query(data: unknown) {
  return {
    data,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }
}

beforeEach(() => {
  vi.mocked(useClassTwrAvailability).mockReturnValue(query([
    {
      asset_type: 'ACAO',
      available: true,
      engine_supported: true,
      data_available: true,
      latest_snapshot_date: '2026-07-18',
      status: 'available',
      reason: null,
    },
    {
      asset_type: 'TESOURO_DIRETO',
      available: false,
      engine_supported: false,
      data_available: false,
      latest_snapshot_date: null,
      status: 'dedicated_history_not_available',
      reason: 'Motor histórico dedicado ainda indisponível.',
    },
  ]) as ReturnType<typeof useClassTwrAvailability>)
  vi.mocked(useDailyEvolution).mockReturnValue(query([]) as ReturnType<typeof useDailyEvolution>)
  vi.mocked(useMonthlyEvolution).mockReturnValue(query([{ date: '2026-07-18' }]) as ReturnType<typeof useMonthlyEvolution>)
  vi.mocked(useClassDailyEvolution).mockReturnValue(query([]) as ReturnType<typeof useClassDailyEvolution>)
  vi.mocked(useClassMonthlyEvolution).mockReturnValue(query([{ date: '2026-07-18' }]) as ReturnType<typeof useClassMonthlyEvolution>)
})

describe('PortfolioEvolutionSection', () => {
  it('alterna do consolidado para a consulta mensal por classe', () => {
    render(<PortfolioEvolutionSection portfolioId={46} />)

    expect(screen.getByText('gráfico mensal: 1')).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Classe do histórico'), {
      target: { value: 'ACAO' },
    })

    expect(useMonthlyEvolution).toHaveBeenLastCalledWith(null, '12m')
    expect(useClassMonthlyEvolution).toHaveBeenLastCalledWith(46, 'ACAO', '12m')
    expect(screen.getAllByText('Ações')).toHaveLength(2)
  })

  it('explica classe sem motor histórico sem disparar consulta de série', () => {
    render(<PortfolioEvolutionSection portfolioId={46} />)
    fireEvent.change(screen.getByLabelText('Classe do histórico'), {
      target: { value: 'TESOURO_DIRETO' },
    })

    expect(screen.getByText('Motor histórico dedicado ainda indisponível.')).toBeTruthy()
    expect(useClassMonthlyEvolution).toHaveBeenLastCalledWith(46, null, '12m')
  })
})
