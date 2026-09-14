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
    'mantem a escolha de classe compacta em %ipx',
    (width) => {
      window.innerWidth = width
      setup()

      const classSelect = screen.getByRole('combobox', { name: /Tipo de ativo/i })
      const buyButton = screen.getByRole('button', { name: /Compra/i })
      const sellButton = screen.getByRole('button', { name: /Venda/i })

      expect(classSelect).toBeTruthy()
      expect(classSelect).toHaveProperty('value', 'acao')
      expect(buyButton).toBeTruthy()
      expect(sellButton).toBeTruthy()
      expect(buyButton.compareDocumentPosition(classSelect) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
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
      const classKeyByLabel: Record<string, string> = {
        Ação: 'acao',
        FII: 'fii',
        'ETF BR': 'etf_br',
        BDR: 'bdr',
        Stock: 'stock',
        'ETF INT': 'etf_int',
        Cripto: 'cripto',
      }

      fireEvent.change(screen.getByRole('combobox', { name: /Tipo de ativo/i }), {
        target: { value: classKeyByLabel[label] },
      })
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

    fireEvent.change(screen.getByRole('combobox', { name: /Tipo de ativo/i }), {
      target: { value: 'cripto' },
    })
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
