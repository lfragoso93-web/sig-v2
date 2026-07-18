import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ResumePage from './ResumePage'

const mocks = vi.hoisted(() => ({
  usePortfolioList: vi.fn(),
  usePortfolioSummaryData: vi.fn(),
  usePositions: vi.fn(),
  useMonthlyEvolution: vi.fn(),
  useClassMonthlyEvolution: vi.fn(),
  useClassTwrAvailability: vi.fn(),
  setSelectedPortfolioId: vi.fn(),
}))

vi.mock('@/hooks/usePortfolio', () => ({
  usePortfolioList: mocks.usePortfolioList,
  usePortfolioSummaryData: mocks.usePortfolioSummaryData,
  usePositions: mocks.usePositions,
}))

vi.mock('@/hooks/useEvolution', () => ({
  useMonthlyEvolution: mocks.useMonthlyEvolution,
  useClassMonthlyEvolution: mocks.useClassMonthlyEvolution,
  useClassTwrAvailability: mocks.useClassTwrAvailability,
}))

vi.mock('@/store/appStore', () => ({
  useAppStore: (selector: (state: {
    selectedPortfolioId: number
    setSelectedPortfolioId: (id: number) => void
  }) => unknown) => selector({
    selectedPortfolioId: 46,
    setSelectedPortfolioId: mocks.setSelectedPortfolioId,
  }),
}))

vi.mock('@/components/ui/KpiCard', () => ({
  default: ({ label, bottomLine }: { label: string; bottomLine?: React.ReactNode }) => (
    <div>
      <span>{label}</span>
      {bottomLine}
    </div>
  ),
}))

vi.mock('@/components/ui/SkeletonCard', () => ({
  default: () => <div data-testid="kpi-skeleton" />,
}))

vi.mock('@/components/charts/PatrimonioBarChart', () => ({
  default: ({ data }: { data: Array<{ history_source?: string }> }) => (
    <div data-testid="patrimonio-chart">{data[0]?.history_source}</div>
  ),
}))

vi.mock('@/components/resume/PositionTable', () => ({
  default: () => <div data-testid="position-table" />,
}))

vi.mock('@/components/modals/CreatePortfolioModal', () => ({
  default: () => null,
}))

describe('ResumePage position states', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.usePortfolioList.mockReturnValue({
      data: [{ id: 46, name: 'Carteira principal' }],
      isLoading: false,
    })
    mocks.usePortfolioSummaryData.mockReturnValue({
      data: undefined,
      isLoading: false,
    })
    mocks.useMonthlyEvolution.mockReturnValue({
      data: [],
      isLoading: false,
    })
    mocks.useClassMonthlyEvolution.mockReturnValue({
      data: [],
      isLoading: false,
    })
    mocks.useClassTwrAvailability.mockReturnValue({
      data: [],
      isLoading: false,
    })
    mocks.usePositions.mockReturnValue({
      data: [],
      isLoading: false,
    })
  })

  it('usa snapshots mensais consolidados como fonte padrão', () => {
    mocks.useMonthlyEvolution.mockReturnValue({
      data: [{ history_source: 'portfolio_snapshot' }],
      isLoading: false,
    })

    render(<ResumePage />)

    expect(mocks.useMonthlyEvolution).toHaveBeenCalledWith(46, '12m')
    expect(screen.getByTestId('patrimonio-chart').textContent).toBe('portfolio_snapshot')
  })

  it('usa snapshots de classe somente quando a classe está disponível', () => {
    mocks.useClassTwrAvailability.mockReturnValue({
      data: [{
        asset_type: 'FII',
        available: true,
        engine_supported: true,
        data_available: true,
        latest_snapshot_date: '2026-07-17',
        status: 'available',
        reason: null,
      }],
      isLoading: false,
    })
    mocks.useClassMonthlyEvolution.mockReturnValue({
      data: [{ history_source: 'portfolio_class_snapshot' }],
      isLoading: false,
    })

    render(<ResumePage />)
    fireEvent.change(screen.getAllByRole('combobox')[0], {
      target: { value: 'FII' },
    })

    expect(mocks.useClassMonthlyEvolution).toHaveBeenLastCalledWith(46, 'FII', '12m')
    expect(screen.getByTestId('patrimonio-chart').textContent).toBe('portfolio_class_snapshot')
  })

  it('não consulta recomposição quando o snapshot da classe está indisponível', () => {
    mocks.useClassTwrAvailability.mockReturnValue({
      data: [{
        asset_type: 'FII',
        available: false,
        engine_supported: true,
        data_available: false,
        latest_snapshot_date: null,
        status: 'awaiting_backfill',
        reason: 'Histórico ainda não materializado.',
      }],
      isLoading: false,
    })

    render(<ResumePage />)
    fireEvent.change(screen.getAllByRole('combobox')[0], {
      target: { value: 'FII' },
    })

    expect(mocks.useClassMonthlyEvolution).toHaveBeenLastCalledWith(46, null, '12m')
    expect(screen.getByText('Histórico ainda não materializado.')).toBeTruthy()
  })

  it('mantém skeletons enquanto as posições ainda estão carregando', () => {
    mocks.usePositions.mockReturnValue({
      data: undefined,
      isLoading: true,
    })

    const { container } = render(<ResumePage />)

    expect(screen.queryByText('Nenhum ativo encontrado')).toBeNull()
    expect(container.querySelectorAll('.animate-pulse')).toHaveLength(3)
  })

  it('exibe estado vazio somente após uma resposta vazia real', () => {
    render(<ResumePage />)

    expect(screen.getByText('Nenhum ativo encontrado')).toBeTruthy()
    expect(screen.getByText(/Adicione um lançamento/)).toBeTruthy()
  })

  it('explicita contrato summary.v2 inválido sem renderizar KPIs zerados', () => {
    mocks.usePortfolioSummaryData.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('Contrato summary.v2 inválido: total_patrimonio'),
    })

    render(<ResumePage />)

    expect(screen.getByText(/Contrato financeiro inválido/)).toBeTruthy()
    expect(screen.getByText(/total_patrimonio/)).toBeTruthy()
    expect(screen.queryByText('Patrimônio Total')).toBeNull()
  })

  it('não apresenta retorno estimado como TWR', () => {
    mocks.usePortfolioSummaryData.mockReturnValue({
      data: {
        rentabilidade_total: 12.5,
        rentabilidade_source: 'valuation_fallback',
        return_is_estimated: true,
      },
      isLoading: false,
    })

    render(<ResumePage />)

    expect(screen.getByText('Retorno estimado')).toBeTruthy()
    expect(screen.getByText(/TWR indisponível sem snapshot/)).toBeTruthy()
    expect(screen.queryByText('Rentabilidade (TWR)')).toBeNull()
  })

  it('explicita cobertura parcial e os ativos sem preço', () => {
    mocks.usePortfolioSummaryData.mockReturnValue({
      data: {
        has_partial_prices: true,
        assets_without_price: ['PETR4', 'VALE3'],
      },
      isLoading: false,
    })

    render(<ResumePage />)

    expect(screen.getByText(/PETR4, VALE3/)).toBeTruthy()
    expect(screen.getByText(/valor investido é usado como referência/)).toBeTruthy()
  })
})
