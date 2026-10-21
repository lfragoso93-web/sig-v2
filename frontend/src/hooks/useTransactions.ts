import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/services/api'

export interface Transaction {
  id: number
  portfolio_id: number
  ticker: string
  asset_type: string
  operation: 'buy' | 'sell'
  quantity: number
  price: number
  fees: number
  date: string
  currency: string
  notes?: string | null
  fixed_income_contract_id?: number | null
}

export interface FixedIncomeContract {
  id: number
  portfolio_id: number
  display_name: string
  product_type: string
  issuer?: string | null
  indexer?: string | null
  rate_value?: number | string | null
  rate_unit?: string | null
  maturity_date?: string | null
  liquidity_type?: string | null
  grace_period_end?: string | null
  tax_exempt?: boolean | null
  currency: string
}

export type FixedIncomeContractCreate = Omit<FixedIncomeContract, 'id' | 'portfolio_id'>

export interface PagedTransactions {
  items:     Transaction[]
  total:     number
  page:      number
  page_size: number
  pages:     number
}

export interface TransactionCreate {
  ticker: string
  asset_type: string
  /** 'buy' | 'sell' ou tipo estendido (COMPRA/VENDA/BONIFICACAO…) */
  operation: string
  quantity: number
  price: number
  fees?: number
  date: string
  currency?: string
  fx_rate?: number
  notes?: string | null
  fixed_income_contract_id?: number | null
  fixed_income_contract?: FixedIncomeContractCreate | null
}

export type TransactionUpdate = Partial<TransactionCreate>

export interface TransactionFilters {
  page?:       number
  page_size?:  number
  asset_type?: string
  ticker?:     string
  operation?:  'buy' | 'sell' | null
  date_from?:  string | null
  date_to?:    string | null
  sort?:       'asc' | 'desc'
}

const TX_KEY = (pid: number | null, filters?: TransactionFilters) =>
  ['transactions', pid, filters ?? {}]

function invalidatePortfolioKeys(qc: ReturnType<typeof useQueryClient>, portfolioId: number) {
  qc.invalidateQueries({ queryKey: ['transactions',         portfolioId] })
  qc.invalidateQueries({ queryKey: ['transaction-classes',  portfolioId] })
  qc.invalidateQueries({ queryKey: ['fixed-income-contracts', portfolioId] })
  qc.invalidateQueries({ queryKey: ['portfolio-summary',    portfolioId] })
  qc.invalidateQueries({ queryKey: ['positions',            portfolioId] })
  qc.invalidateQueries({ queryKey: ['asset-distribution',   portfolioId] })
  qc.invalidateQueries({ queryKey: ['patrimonio-history',   portfolioId] })
  qc.invalidateQueries({ queryKey: ['summary',              portfolioId] })
  // KPIs usados no ResumePage
  qc.invalidateQueries({ queryKey: ['rentabilidade-kpis',   portfolioId] })
  qc.invalidateQueries({ queryKey: ['rentabilidade-ativos', portfolioId] })
  qc.invalidateQueries({ queryKey: ['rentabilidade-classes',portfolioId] })
  // Metas financeiras (current_value automático pode mudar após transação)
  qc.invalidateQueries({ queryKey: ['goals',                portfolioId] })
}

export function useTransactions(
  portfolioId: number | null,
  filters: TransactionFilters = {},
) {
  return useQuery<PagedTransactions>({
    queryKey: TX_KEY(portfolioId, filters),
    queryFn: () => {
      const params: Record<string, string | number> = {
        page:      filters.page      ?? 1,
        page_size: filters.page_size ?? 50,
      }
      if (filters.asset_type) params.asset_type = filters.asset_type
      if (filters.ticker)     params.ticker    = filters.ticker
      if (filters.operation)  params.operation = filters.operation
      if (filters.date_from)  params.date_from = filters.date_from
      if (filters.date_to)    params.date_to   = filters.date_to
      if (filters.sort)       params.sort      = filters.sort
      return api
        .get(`/portfolios/${portfolioId}/transactions`, { params })
        .then(r => r.data)
    },
    enabled: !!portfolioId,
    placeholderData: prev => prev,
  })
}

export interface TransactionClassSummary {
  asset_type: string
  label: string
  count: number
}

export function useTransactionClasses(portfolioId: number | null) {
  return useQuery<TransactionClassSummary[]>({
    queryKey: ['transaction-classes', portfolioId],
    queryFn: () => api
      .get(`/portfolios/${portfolioId}/transactions/classes`)
      .then(r => r.data),
    enabled: !!portfolioId,
  })
}

export function useFixedIncomeContracts(portfolioId: number | null, enabled = true) {
  return useQuery<FixedIncomeContract[]>({
    queryKey: ['fixed-income-contracts', portfolioId],
    queryFn: () => api
      .get(`/portfolios/${portfolioId}/fixed-income-contracts`)
      .then(r => r.data),
    enabled: !!portfolioId && enabled,
  })
}

export function useCreateTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ portfolioId, data }: { portfolioId: number; data: TransactionCreate }) =>
      api.post<Transaction>(`/portfolios/${portfolioId}/transactions`, data).then(r => r.data),
    onSuccess: (_d, v) => invalidatePortfolioKeys(qc, v.portfolioId),
  })
}

export function useUpdateTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ portfolioId, id, data }: { portfolioId: number; id: number; data: TransactionUpdate }) =>
      api.patch<Transaction>(`/portfolios/${portfolioId}/transactions/${id}`, data).then(r => r.data),
    onSuccess: (_d, v) => invalidatePortfolioKeys(qc, v.portfolioId),
  })
}

export function useDeleteTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ portfolioId, id }: { portfolioId: number; id: number }) =>
      api.delete(`/portfolios/${portfolioId}/transactions/${id}`).then(r => r.data),
    onSuccess: (_d, v) => invalidatePortfolioKeys(qc, v.portfolioId),
  })
}
