import api from './api'

export type TransactionType = 'COMPRA' | 'VENDA' | 'BONIFICACAO' | 'DESDOBRAMENTO' | 'GRUPAMENTO'

export interface TransactionCreate {
  ticker: string
  asset_type: string
  transaction_type: TransactionType
  quantity: number
  price: number
  transaction_date: string
  broker?: string
  fees?: number
  notes?: string
}

export interface TransactionOut {
  id: number
  portfolio_id: number
  ticker: string
  asset_type: string
  transaction_type: string
  quantity: number
  price: number
  total_value: number
  fees: number
  transaction_date: string
  broker: string | null
  notes: string | null
  average_price_after: number | null
}

export const transactionService = {
  create: (portfolioId: number, data: TransactionCreate) =>
    api.post<TransactionOut>(`/api/v1/portfolios/${portfolioId}/transactions`, data).then(r => r.data),

  list: (portfolioId: number, params?: { ticker?: string; asset_type?: string; tx_type?: string; year?: number }) =>
    api.get<TransactionOut[]>(`/api/v1/portfolios/${portfolioId}/transactions`, { params }).then(r => r.data),

  delete: (txId: number) =>
    api.delete(`/api/v1/transactions/${txId}`),
}
