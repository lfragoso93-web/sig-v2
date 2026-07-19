import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProventosPage from './ProventosPage'

const state = vi.hoisted(() => ({
  portfolioId: 1 as number | null,
  summary: vi.fn(),
  distribution: vi.fn(),
  history: vi.fn(),
  list: vi.fn(),
}))

vi.mock('@/store/appStore', () => ({
  useAppStore: (selector: (value: { selectedPortfolioId: number | null }) => unknown) =>
    selector({ selectedPortfolioId: state.portfolioId }),
}))

vi.mock('@/hooks/useProventos', () => ({
  useProventosSummary: (...args: unknown[]) => state.summary(...args),
  useProventosDistribuicao: (...args: unknown[]) => state.distribution(...args),
  useProventosHistoricoMensal: (...args: unknown[]) => state.history(...args),
  useProventosList: (...args: unknown[]) => state.list(...args),
}))

vi.mock('@/components/ui/KpiCard', () => ({
  default: ({ label, value }: { label: string; value: string }) => (
    <div>{label}: {value}</div>
  ),
}))

vi.mock('@/components/ui/EmptyState', () => ({
  default: ({ title }: { title: string }) => <div>{title}</div>,
}))

vi.mock('@/components/charts/ProventosDonutChart', () => ({
  default: ({ data }: { data: unknown[] }) => <div>distribution:{data.length}</div>,
}))

vi.mock('@/components/proventos/ProventosHistoricoTable', () => ({
  default: ({ data }: { data: unknown[] }) => <div>history:{data.length}</div>,
}))

vi.mock('@/components/proventos/MeusProventosTable', () => ({
  default: ({ data }: { data: unknown[] }) => <div>items:{data.length}</div>,
}))

const summary = {
  total_recebido: 100,
  total_liquido_recebido: 85,
  total_bruto_recebido: 100,
  total_a_receber: 50,
  total_liquido_a_receber: 50,
  total_bruto_a_receber: 50,
  total_12m: 135,
  media_mensal_12m: 11.25,
  eventos_nao_cash: 2,
}

function setSuccessState() {
  state.summary.mockReturnValue({ data: summary, isLoading: false, isError: false })
  state.distribution.mockReturnValue({ data: [], isLoading: false, isError: false })
  state.history.mockReturnValue({ data: [], isLoading: false, isError: false })
  state.list.mockReturnValue({
    data: { total: 0, page: 1, page_size: 20, items: [] },
    isLoading: false,
    isError: false,
  })
}

describe('ProventosPage', () => {
  beforeEach(() => {
    state.portfolioId = 1
    vi.clearAllMocks()
    setSuccessState()
  })

  it('renders the explicit empty states', () => {
    render(<ProventosPage />)

    expect(screen.getByText('Sem distribuição para os filtros selecionados.')).toBeTruthy()
    expect(screen.getByText('history:0')).toBeTruthy()
    expect(screen.getByText('items:0')).toBeTruthy()
  })

  it('renders loading states without showing zero-valued KPIs', () => {
    state.summary.mockReturnValue({ data: undefined, isLoading: true, isError: false })
    state.distribution.mockReturnValue({ data: undefined, isLoading: true, isError: false })
    state.history.mockReturnValue({ data: undefined, isLoading: true, isError: false })
    state.list.mockReturnValue({ data: undefined, isLoading: true, isError: false })

    render(<ProventosPage />)

    expect(screen.getAllByTestId('proventos-kpi-loading')).toHaveLength(4)
    expect(screen.getByTestId('proventos-distribution-loading')).toBeTruthy()
    expect(screen.queryByText(/Recebido líquido:/)).toBeNull()
  })

  it('renders errors for every independent query', () => {
    state.summary.mockReturnValue({ data: undefined, isLoading: false, isError: true })
    state.distribution.mockReturnValue({ data: undefined, isLoading: false, isError: true })
    state.history.mockReturnValue({ data: undefined, isLoading: false, isError: true })
    state.list.mockReturnValue({ data: undefined, isLoading: false, isError: true })

    render(<ProventosPage />)

    expect(screen.getAllByRole('alert')).toHaveLength(4)
  })

  it('sends one filter universe to all hooks and exposes accessible controls', () => {
    render(<ProventosPage />)

    fireEvent.click(screen.getByRole('button', { name: 'Recebidos' }))
    fireEvent.change(screen.getByLabelText('Tipo de ativo'), { target: { value: 'FII' } })
    fireEvent.change(screen.getByLabelText('Tipo de provento'), { target: { value: 'RENDIMENTO' } })

    const expectedFilters = {
      status: 'RECEBIDO',
      year: undefined,
      asset_type: 'FII',
      dividend_type: 'RENDIMENTO',
    }
    expect(state.summary).toHaveBeenLastCalledWith(1, expectedFilters)
    expect(state.distribution).toHaveBeenLastCalledWith(1, 12, expectedFilters)
    expect(state.history).toHaveBeenLastCalledWith(1, expectedFilters)
    expect(state.list).toHaveBeenLastCalledWith(1, {
      ...expectedFilters,
      page: 1,
      page_size: 20,
    })
    expect(screen.getByRole('button', { name: 'Recebidos' }).getAttribute('aria-pressed')).toBe('true')
  })

  it('requires a selected portfolio before querying data', () => {
    state.portfolioId = null

    render(<ProventosPage />)

    expect(screen.getByText('Nenhuma carteira selecionada')).toBeTruthy()
  })
})
