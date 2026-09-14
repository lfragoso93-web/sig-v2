import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AddTransactionModal from './AddTransactionModal'
import { useAppStore } from '@/store/appStore'

const createTransaction = vi.fn()
const updateTransaction = vi.fn()

vi.mock('@/hooks/useTransactions', () => ({
  useCreateTransaction: () => ({ mutateAsync: createTransaction, isPending: false }),
  useUpdateTransaction: () => ({ mutateAsync: updateTransaction, isPending: false }),
}))

vi.mock('@/hooks/useTickerQuote', () => ({
  useTickerQuote: () => ({ quote: null, loading: false, error: null }),
}))

vi.mock('@/hooks/useTesouroSearch', () => ({
  useTesouroSearch: () => ({ items: [], loading: false, error: null }),
}))

vi.mock('@/hooks/useTickerSuggest', () => ({
  useTickerSuggest: () => ({ items: [], loading: false, error: null }),
}))

vi.mock('@/hooks/useTreasuryPrice', () => ({
  useTreasuryPrice: () => ({ price: null, rate: null, loading: false, error: null }),
}))

function setup() {
  useAppStore.setState({
    selectedPortfolioId: 42,
    transactionModal: { open: true, prefill: undefined },
  })
  createTransaction.mockResolvedValue({ id: 1 })
  updateTransaction.mockResolvedValue({ id: 1 })

  render(<AddTransactionModal onClose={vi.fn()} />)
}

async function submitSimpleTransaction() {
  fireEvent.change(screen.getAllByRole('textbox')[0], {
    target: { value: 'abc' },
  })
  fireEvent.change(screen.getByPlaceholderText('0'), {
    target: { value: '1' },
  })
  fireEvent.change(screen.getAllByPlaceholderText('0,00')[0], {
    target: { value: '10' },
  })
  fireEvent.click(screen.getByRole('button', { name: /Salvar/i }))

  await waitFor(() => expect(createTransaction).toHaveBeenCalledTimes(1))
}

describe('AddTransactionModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it.each([375, 430])(
    'mantem as abas de classe rolaveis em %ipx',
    (width) => {
      window.innerWidth = width
      setup()

      const criptoTab = screen.getByRole('button', { name: /Cripto/i })
      const tabList = criptoTab.parentElement

      expect(tabList?.style.display).toBe('flex')
      expect(tabList?.style.flexWrap).toBe('nowrap')
      expect(tabList?.style.overflowX).toBe('auto')
      expect(tabList?.style.overflowY).toBe('hidden')
      expect(criptoTab.style.flexShrink).toBe('0')
      expect(criptoTab.style.whiteSpace).toBe('nowrap')
    },
  )

  it.each([
    ['Ação', 'ACAO', 'BRL'],
    ['FII', 'FII', 'BRL'],
    ['ETF BR', 'ETF_NACIONAL', 'BRL'],
    ['BDR', 'BDR', 'BRL'],
    ['Stock', 'STOCK', 'USD'],
    ['ETF INT', 'ETF_INTERNACIONAL', 'USD'],
    ['Cripto', 'CRIPTO', 'BRL'],
  ])(
    'envia asset_type %s apos trocar a classe no modal',
    async (label, assetType, currency) => {
      setup()

      fireEvent.click(screen.getByRole('button', { name: label }))
      await submitSimpleTransaction()

      expect(createTransaction).toHaveBeenCalledWith({
        portfolioId: 42,
        data: expect.objectContaining({
          ticker: 'ABC',
          asset_type: assetType,
          operation: 'buy',
          quantity: 1,
          price: 10,
          currency,
        }),
      })
    },
  )

  it('envia a classe canonica selecionada no payload de lancamento', async () => {
    setup()

    fireEvent.click(screen.getByRole('button', { name: /Cripto/i }))
    fireEvent.change(screen.getByPlaceholderText(/BTC ou Bitcoin/i), {
      target: { value: 'btc' },
    })
    fireEvent.change(screen.getByPlaceholderText('0'), {
      target: { value: '0.5' },
    })
    fireEvent.change(screen.getAllByPlaceholderText('0,00')[0], {
      target: { value: '100000' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Salvar/i }))

    await waitFor(() => expect(createTransaction).toHaveBeenCalledTimes(1))
    expect(createTransaction).toHaveBeenCalledWith({
      portfolioId: 42,
      data: expect.objectContaining({
        ticker: 'BTC',
        asset_type: 'CRIPTO',
        operation: 'buy',
        quantity: 0.5,
        price: 100000,
        currency: 'BRL',
      }),
    })
  })
})
