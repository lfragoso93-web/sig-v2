import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { makePortfolioSummary } from '@/test/fixtures/portfolioSummary'
import PatrimonioPage from './PatrimonioPage'

const mocks = vi.hoisted(() => ({
  usePortfolioSummary: vi.fn(),
  useAssetDistribution: vi.fn(),
  usePositions: vi.fn(),
  useClassTargets: vi.fn(),
}))

vi.mock('@/hooks/usePortfolio', () => ({
  usePortfolioSummary: mocks.usePortfolioSummary,
  useAssetDistribution: mocks.useAssetDistribution,
  usePositions: mocks.usePositions,
}))

vi.mock('@/hooks/useClassTargets', () => ({
  useClassTargets: mocks.useClassTargets,
}))

vi.mock('@/store/appStore', () => ({
  useAppStore: (selector: (state: { selectedPortfolioId: number | null }) => unknown) =>
    selector({ selectedPortfolioId: 46 }),
}))

vi.mock('@/components/charts/AssetDonutChart', () => ({
  default: () => <div data-testid="asset-donut-chart" />,
}))

vi.mock('@/components/charts/PortfolioEvolutionSection', () => ({
  default: () => <div data-testid="portfolio-evolution-section" />,
}))

vi.mock('@/components/portfolio/PortfolioReconciliationPanel', () => ({
  default: () => <div data-testid="reconciliation-panel" />,
}))

vi.mock('@/components/portfolio/PendingCorporateFractionsPanel', () => ({
  default: () => <div data-testid="pending-fractions-panel" />,
}))

vi.mock('@/components/resume/PositionTable', () => ({
  default: () => <div data-testid="patrimonio-position-table" />,
}))

vi.mock('@/components/portfolio/AssetDetailDrawer', () => ({
  default: ({ ticker }: { ticker?: string | null }) => (
    <div data-testid="asset-detail-drawer">{ticker}</div>
  ),
}))

describe('PatrimonioPage card layout (#90 & #351)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.usePortfolioSummary.mockReturnValue({
      data: makePortfolioSummary({
        total_patrimonio: 150000,
        total_investido: 120000,
        ganho_nao_realizado: 30000,
        variacao_percentual: 25,
        lucro_total: 35000,
        ganho_realizado: 2000,
        total_proventos: 3000,
        rentabilidade_total: 18.4,
        price_coverage_pct: 100,
      }),
      isLoading: false,
      error: null,
    })
    mocks.useAssetDistribution.mockReturnValue({
      data: [
        { asset_type: 'ACAO', label: 'Ações', value: 90000, percentage: 60, color: '#01696f' },
        { asset_type: 'FII', label: 'FIIs', value: 60000, percentage: 40, color: '#006494' },
      ],
      isLoading: false,
    })
    mocks.useClassTargets.mockReturnValue({
      data: [
        {
          asset_type: 'ACAO',
          label: 'Ações',
          color: '#01696f',
          current_pct: 60,
          target_pct: 55,
          delta_pct: 5,
        },
      ],
      isLoading: false,
    })
    mocks.usePositions.mockReturnValue({
      data: [
        {
          label: 'Ações',
          count: 1,
          total_value: 90000,
          total_invested: 70000,
          positions: [
            {
              id: 1,
              ticker: 'WEGE3',
              asset_type: 'ACAO',
              asset_label: 'WEG S.A.',
              quantity: 1000,
              average_price: 70,
              current_price: 90,
              current_value: 90000,
              invested_value: 70000,
              variation_value: 20000,
              variation_percent: 28.57,
              allocation_pct: 60,
            },
          ],
        },
      ],
      isLoading: false,
    })
  })

  it('visually separates consolidation, allocation targets, concentration, evolution and positions cards', () => {
    render(
      <MemoryRouter>
        <PatrimonioPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('region', { name: 'Destaques e oportunidades da carteira' })).toBeTruthy()
    expect(screen.getByText('Destaques da carteira')).toBeTruthy()
    expect(screen.getByText('Posições no lucro')).toBeTruthy()
    expect(screen.getByText('Oportunidades de compra')).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Consolidação do patrimônio' })).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Alocação ideal versus atual' })).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Índice de concentração' })).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Maiores posições da carteira' })).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Posições da carteira' })).toBeTruthy()
    expect(screen.getByTestId('patrimonio-position-table')).toBeTruthy()
  })

  it('opens AssetDetailDrawer when clicking a Top 5 position ticker', () => {
    render(
      <MemoryRouter>
        <PatrimonioPage />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getAllByRole('button', { name: 'WEGE3' })[0])
    expect(screen.getByTestId('asset-detail-drawer').textContent).toBe('WEGE3')
  })
})
