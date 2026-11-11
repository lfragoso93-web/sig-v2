import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Transacoes, { computeDateRange } from './Transacoes'

const mocks = vi.hoisted(() => ({
  useTransactions: vi.fn(),
  useTransactionClasses: vi.fn(),
  useDeleteTransaction: vi.fn(),
  useBulkDeleteTransactions: vi.fn(),
  usePortfolios: vi.fn(),
  useAppStore: vi.fn(),
}))

vi.mock('react-router-dom', () => ({
  useSearchParams: () => [new URLSearchParams()],
}))

vi.mock('@/store/appStore', () => ({
  useAppStore: () => mocks.useAppStore(),
}))

vi.mock('@/hooks/usePortfolios', () => ({
  usePortfolios: () => mocks.usePortfolios(),
}))

vi.mock('@/hooks/useTransactions', () => ({
  useTransactions: (portfolioId: number | null, filters?: any) => mocks.useTransactions(portfolioId, filters),
  useTransactionClasses: (portfolioId: number | null) => mocks.useTransactionClasses(portfolioId),
  useDeleteTransaction: () => mocks.useDeleteTransaction(),
  useBulkDeleteTransactions: () => mocks.useBulkDeleteTransactions(),
}))

vi.mock('@/components/charts/TransactionsBarChart', () => ({
  default: () => <div data-testid="transactions-bar-chart" />,
}))

describe('Transacoes page with independent per-class pagination', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    mocks.useAppStore.mockReturnValue({
      selectedPortfolioId: 1,
      openTransactionModal: vi.fn(),
    })

    mocks.usePortfolios.mockReturnValue({
      data: [{ id: 1, name: 'Principal' }],
    })

    mocks.useDeleteTransaction.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    })

    mocks.useBulkDeleteTransactions.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({ deleted_count: 1, earliest_date: '2024-01-15' }),
      isPending: false,
    })

    mocks.useTransactionClasses.mockReturnValue({
      data: [
        { asset_type: 'ACAO', label: 'Ações', count: 30 },
        { asset_type: 'FII', label: 'FIIs', count: 5 },
      ],
      isLoading: false,
    })

    mocks.useTransactions.mockImplementation((portfolioId, filters) => {
      if (filters?.asset_type === 'ACAO') {
        return {
          data: {
            items: [
              {
                id: 101,
                ticker: 'PETR4',
                asset_type: 'ACAO',
                operation: 'buy',
                quantity: 100,
                price: 35.0,
                fees: 0,
                date: '2024-01-15',
                currency: 'BRL',
              },
            ],
            total: 30,
            page: filters.page ?? 1,
            page_size: 15,
            pages: 2,
          },
          isLoading: false,
        }
      }

      if (filters?.asset_type === 'FII') {
        return {
          data: {
            items: [
              {
                id: 201,
                ticker: 'HGLG11',
                asset_type: 'FII',
                operation: 'buy',
                quantity: 10,
                price: 160.0,
                fees: 0,
                date: '2024-02-10',
                currency: 'BRL',
              },
            ],
            total: 5,
            page: filters.page ?? 1,
            page_size: 15,
            pages: 1,
          },
          isLoading: false,
        }
      }

      // Global query for charts
      return {
        data: {
          items: [],
          total: 35,
          page: 1,
          page_size: 100,
          pages: 1,
        },
        isLoading: false,
      }
    })
  })

  it('renders class sections for each asset class in the portfolio', () => {
    render(<Transacoes />)

    expect(screen.getByTestId('class-section-ACAO')).toBeTruthy()
    expect(screen.getByTestId('class-section-FII')).toBeTruthy()
    expect(screen.getAllByText('PETR4')[0]).toBeTruthy()
    expect(screen.getAllByText('HGLG11')[0]).toBeTruthy()
  })

  it('provides independent pagination controls per class', async () => {
    render(<Transacoes />)

    // Ações has 2 pages (30 items with page_size 15)
    const acaoSection = screen.getByTestId('class-section-ACAO')
    expect(acaoSection.textContent).toContain('1 / 2')

    // FII has only 1 page (5 items), so pagination is not rendered or shows 1 page
    const fiiSection = screen.getByTestId('class-section-FII')
    expect(fiiSection.textContent).not.toContain('/ 2')

    // Click next page on Ações
    const nextBtn = acaoSection.querySelector('button[aria-label="Próxima página"]')
    expect(nextBtn).toBeTruthy()
    fireEvent.click(nextBtn!)

    await waitFor(() => {
      expect(mocks.useTransactions).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          asset_type: 'ACAO',
          page: 2,
        }),
      )
    })
  })
  it('calcula intervalos de data corretamente na funcao utilitaria computeDateRange', () => {
    const ref = new Date('2026-06-15T12:00:00Z')

    expect(computeDateRange('all', undefined, undefined, ref)).toEqual({})
    expect(computeDateRange('custom', '2026-01-01', '2026-03-31', ref)).toEqual({
      dateFrom: '2026-01-01',
      dateTo: '2026-03-31',
    })

    const ytd = computeDateRange('ytd', undefined, undefined, ref)
    expect(ytd.dateFrom).toBe('2026-01-01')
    expect(ytd.dateTo).toBe('2026-06-15')

    const d30 = computeDateRange('30d', undefined, undefined, ref)
    expect(d30.dateTo).toBe('2026-06-15')
    expect(d30.dateFrom).toBe('2026-05-16')
  })

  it('aplica filtro temporal predefinido e consulta transacoes com date_from e date_to', async () => {
    render(<Transacoes />)

    const periodSelect = screen.getByLabelText('Filtro temporal') as HTMLSelectElement
    expect(periodSelect.value).toBe('all')

    fireEvent.change(periodSelect, { target: { value: '30d' } })

    await waitFor(() => {
      expect(mocks.useTransactions).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          date_from: expect.any(String),
          date_to: expect.any(String),
        }),
      )
    })
  })

  it('exibe campos de data inicial e final ao selecionar Personalizado e envia filtros', async () => {
    render(<Transacoes />)

    const periodSelect = screen.getByLabelText('Filtro temporal') as HTMLSelectElement
    fireEvent.change(periodSelect, { target: { value: 'custom' } })

    const dateFromInput = screen.getByLabelText('Data inicial') as HTMLInputElement
    const dateToInput = screen.getByLabelText('Data final') as HTMLInputElement

    expect(dateFromInput).toBeTruthy()
    expect(dateToInput).toBeTruthy()

    fireEvent.change(dateFromInput, { target: { value: '2026-01-01' } })
    fireEvent.change(dateToInput, { target: { value: '2026-06-01' } })

    await waitFor(() => {
      expect(mocks.useTransactions).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          date_from: '2026-01-01',
          date_to: '2026-06-01',
        }),
      )
    })
  })
it('permite selecionar transacoes e excluir em lote via endpoint bulk-delete', async () => {
    const bulkMutate = vi.fn().mockResolvedValue({ deleted_count: 1, earliest_date: '2024-01-15' })
    mocks.useBulkDeleteTransactions.mockReturnValue({
      mutateAsync: bulkMutate,
      isPending: false,
    })

    render(<Transacoes />)

    const checkboxes = screen.getAllByLabelText('Selecionar transação PETR4')
    fireEvent.click(checkboxes[0])

    expect(screen.getByText('1 transação(ões) selecionada(s)')).toBeTruthy()
    fireEvent.click(screen.getByText('Excluir selecionadas'))
    expect(screen.getByText('Excluir 1 transação(ões)?')).toBeTruthy()
    fireEvent.click(screen.getByText('Excluir em lote'))

    await waitFor(() => {
      expect(bulkMutate).toHaveBeenCalledWith({
        portfolioId: 1,
        data: { transaction_ids: [101] },
      })
    })
  })

  it('permite excluir todas as transacoes filtradas de uma classe em um clique', async () => {
    const bulkMutate = vi.fn().mockResolvedValue({ deleted_count: 30, earliest_date: '2024-01-15' })
    mocks.useBulkDeleteTransactions.mockReturnValue({
      mutateAsync: bulkMutate,
      isPending: false,
    })

    render(<Transacoes />)

    fireEvent.click(screen.getByTestId('delete-group-ACAO'))
    expect(screen.getByText('Excluir 30 transação(ões) de Ações?')).toBeTruthy()
    fireEvent.click(screen.getByText('Excluir em lote'))

    await waitFor(() => {
      expect(bulkMutate).toHaveBeenCalledWith({
        portfolioId: 1,
        data: expect.objectContaining({
          asset_type: 'ACAO',
        }),
      })
    })
  })
})