import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AddTransactionModal from './AddTransactionModal'
import { useAppStore } from '@/store/appStore'

const createTransaction = vi.fn()
const updateTransaction = vi.fn()

vi.mock('@/hooks/useTransactions', () => ({
  useCreateTransaction: () => ({ mutateAsync: createTransaction, isPending: false }),
  useUpdateTransaction: () => ({ mutateAsync: updateTransaction, isPending: false }),
  useFixedIncomeContracts: () => ({
    data: [{
      id: 77,
      portfolio_id: 42,
      display_name: 'CDB existente',
      product_type: 'CDB',
      issuer: 'Banco XP',
      indexer: 'CDI',
      rate_value: 110,
      rate_unit: 'PERCENT_OF_INDEXER',
      maturity_date: '2028-12-31',
      liquidity_type: 'AT_MATURITY',
      grace_period_end: null,
      tax_exempt: false,
      currency: 'BRL',
    }],
    isLoading: false,
  }),
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

  it('cria contrato estruturado junto com uma nova transacao de renda fixa', async () => {
    setup()
    fireEvent.change(screen.getByRole('combobox', { name: /Tipo de ativo/i }), {
      target: { value: 'renda_fixa' },
    })
    expect(screen.getByLabelText('Tipo de produto de Renda Fixa').compareDocumentPosition(
      screen.getByLabelText('Indexador'),
    ) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    fireEvent.change(screen.getByPlaceholderText('ex: CDB Banco XP 110% CDI'), {
      target: { value: 'CDB Banco XP' },
    })
    fireEvent.change(screen.getByLabelText('Indexador'), { target: { value: 'CDI' } })
    fireEvent.change(screen.getByLabelText('Taxa do contrato'), { target: { value: '110' } })
    fireEvent.change(screen.getByLabelText('Tipo de produto de Renda Fixa'), {
      target: { value: 'LCI' },
    })
    fireEvent.change(screen.getByLabelText('Fim da carência'), {
      target: { value: '2027-02-01' },
    })
    fireEvent.change(screen.getAllByPlaceholderText('0,00')[0], {
      target: { value: '1000' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Salvar/i }))

    await waitFor(() => expect(createTransaction).toHaveBeenCalledTimes(1))
    expect(createTransaction).toHaveBeenCalledWith(expect.objectContaining({
      portfolioId: 42,
      data: expect.objectContaining({
        ticker: 'CDB BANCO XP',
        asset_type: 'RENDA_FIXA',
        quantity: 1,
        price: 1000,
        fixed_income_contract: expect.objectContaining({
          display_name: 'CDB Banco XP',
          product_type: 'LCI',
          indexer: 'CDI',
          rate_value: 110,
          rate_unit: 'PERCENT_OF_INDEXER',
          grace_period_end: '2027-02-01',
          tax_exempt: true,
          issuer: null,
        }),
      }),
    }))
  })

  it('deriva o tratamento tributario do produto sem pedir emissor ou classificacao manual', async () => {
    setup()
    fireEvent.change(screen.getByRole('combobox', { name: /Tipo de ativo/i }), {
      target: { value: 'renda_fixa' },
    })

    const productType = screen.getByLabelText('Tipo de produto de Renda Fixa')
    const indexer = screen.getByLabelText('Indexador')
    expect(productType.compareDocumentPosition(indexer) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.queryByLabelText(/Isenção tributária/i)).toBeNull()
    expect(screen.queryByLabelText(/Emissor/i)).toBeNull()

    fireEvent.change(productType, { target: { value: 'LCI' } })
    expect(screen.getByText(/isento de IR/)).toBeTruthy()

    fireEvent.change(productType, { target: { value: 'CDB' } })
    expect(screen.getByText(/tributavel pela tabela regressiva/)).toBeTruthy()
  })

  it('oculta e limpa a carencia quando a liquidez diaria e marcada', async () => {
    setup()
    fireEvent.change(screen.getByRole('combobox', { name: /Tipo de ativo/i }), {
      target: { value: 'renda_fixa' },
    })
    fireEvent.change(screen.getByPlaceholderText('ex: CDB Banco XP 110% CDI'), { target: { value: 'CDB Teste' } })
    fireEvent.change(screen.getByLabelText('Indexador'), { target: { value: 'CDI' } })
    fireEvent.change(screen.getByLabelText(/Fim da car/), { target: { value: '2027-02-01' } })
    expect(screen.getByLabelText(/Fim da car/)).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /Liquidez/ }))
    expect(screen.queryByLabelText(/Fim da car/)).toBeNull()
    fireEvent.change(screen.getAllByPlaceholderText('0,00')[0], { target: { value: '1000' } })
    fireEvent.click(screen.getByRole('button', { name: /Salvar/i }))

    await waitFor(() => expect(createTransaction).toHaveBeenCalledTimes(1))
    expect(createTransaction).toHaveBeenCalledWith(expect.objectContaining({
      data: expect.objectContaining({
        fixed_income_contract: expect.objectContaining({
          liquidity_type: 'DAILY',
          grace_period_end: null,
        }),
      }),
    }))
  })

  it('preserva valores, vinculo ausente e notas ao editar renda fixa legada', async () => {
    useAppStore.setState({
      selectedPortfolioId: 42,
      transactionModal: {
        open: true,
        prefill: {
          tab: 'renda_fixa',
          ticker: 'CDB LEGADO',
          assetName: 'CDB LEGADO',
          transactionId: 19,
          operation: 'buy',
          quantity: 2,
          price: 50,
          fees: 1,
          date: '2026-09-10',
          notes: 'Indexador: legado | anotacao original',
          currency: 'BRL',
        },
      },
    })
    render(<AddTransactionModal onClose={vi.fn()} />)
    const principal = screen.getByLabelText(/Valor registrado/i)
    expect(principal).toHaveProperty('value', '100')
    expect(principal).toHaveProperty('readOnly', true)

    fireEvent.click(screen.getByRole('button', { name: /Salvar/i }))
    await waitFor(() => expect(updateTransaction).toHaveBeenCalledTimes(1))
    expect(updateTransaction).toHaveBeenCalledWith(expect.objectContaining({
      id: 19,
      data: expect.objectContaining({
        quantity: 2,
        price: 50,
        fixed_income_contract_id: null,
        notes: 'Indexador: legado | anotacao original',
      }),
    }))
  })

  it('preenche automaticamente os termos quando o resumo aponta para contrato unico', async () => {
    useAppStore.setState({
      selectedPortfolioId: 42,
      transactionModal: {
        open: true,
        prefill: {
          tab: 'renda_fixa',
          ticker: 'CDB EXISTENTE',
          assetName: 'CDB existente',
        },
      },
    })

    render(<AddTransactionModal onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText(/Tratamento tributario automatico/)).toBeTruthy()
      expect((screen.getByLabelText('Tipo de produto de Renda Fixa') as HTMLSelectElement).value).toBe('CDB')
      expect((screen.getByLabelText('Indexador') as HTMLSelectElement).value).toBe('CDI')
      expect((screen.getByLabelText('Taxa do contrato') as HTMLInputElement).value).toBe('110')
      expect((screen.getByLabelText('Vencimento') as HTMLInputElement).value).toBe('2028-12-31')
    })
  })

  it('preserva o vinculo existente e a representação contabil ao editar', async () => {
    useAppStore.setState({
      selectedPortfolioId: 42,
      transactionModal: {
        open: true,
        prefill: {
          tab: 'renda_fixa',
          ticker: 'CDB EXISTENTE',
          assetName: 'CDB existente',
          transactionId: 20,
          fixedIncomeContractId: 77,
          operation: 'buy',
          quantity: 4,
          price: 250,
          fees: 2,
          date: '2026-09-11',
          notes: 'Indexador: CDI | 110% do CDI',
          currency: 'BRL',
        },
      },
    })
    render(<AddTransactionModal onClose={vi.fn()} />)
    await waitFor(() => expect(screen.getByLabelText('Indexador')).toHaveProperty('value', 'CDI'))
    expect(screen.getByLabelText(/Valor registrado/i)).toHaveProperty('value', '1000')

    fireEvent.click(screen.getByRole('button', { name: /Salvar/i }))
    await waitFor(() => expect(updateTransaction).toHaveBeenCalledTimes(1))
    expect(updateTransaction).toHaveBeenCalledWith(expect.objectContaining({
      id: 20,
      data: expect.objectContaining({
        quantity: 4,
        price: 250,
        fixed_income_contract_id: 77,
        notes: 'Indexador: CDI | 110% do CDI',
      }),
    }))
  })
})
