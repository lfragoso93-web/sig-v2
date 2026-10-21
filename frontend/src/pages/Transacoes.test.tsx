import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Transacoes from './Transacoes'

const mocks = vi.hoisted(() => ({
  useTransactions: vi.fn(),
  useTransactionClasses: vi.fn(),
  useDeleteTransaction: vi.fn(),
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
})
