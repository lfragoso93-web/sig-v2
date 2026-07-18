import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ResumePage from './ResumePage'

const mocks = vi.hoisted(() => ({
  usePortfolioList: vi.fn(),
  usePortfolioSummaryData: vi.fn(),
  usePatrimonioHistory: vi.fn(),
  usePositions: vi.fn(),
  setSelectedPortfolioId: vi.fn(),
}))

vi.mock('@/hooks/usePortfolio', () => ({
  usePortfolioList: mocks.usePortfolioList,
  usePortfolioSummaryData: mocks.usePortfolioSummaryData,
  usePatrimonioHistory: mocks.usePatrimonioHistory,
  usePositions: mocks.usePositions,
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
  default: () => <div data-testid="patrimonio-chart" />,
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
    mocks.usePatrimonioHistory.mockReturnValue({
      data: [],
      isLoading: false,
    })
    mocks.usePositions.mockReturnValue({
      data: [],
      isLoading: false,
    })
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
