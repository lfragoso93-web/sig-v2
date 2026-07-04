import api from './api'

export interface ProventosSummary {
  total_recebido: number
  total_liquido_recebido?: number
  total_bruto_recebido?: number
  total_a_receber: number
  total_liquido_a_receber?: number
  total_bruto_a_receber?: number
  total_12m: number
  media_mensal_12m: number
  eventos_nao_cash?: number
}

export interface ProventoDistribution {
  ticker: string
  asset_type: string
  total: number
  percentage: number
}

export interface ProventosHistoricoMes {
  year: number
  months: (number | null)[]
  total: number
  media: number
}

export interface ProventoItem {
  id: number
  ticker: string
  asset_type: string
  dividend_type: string
  is_cash?: boolean
  status: 'RECEBIDO' | 'A_RECEBER'
  record_date: string | null
  ex_date: string
  payment_date: string | null
  approved_on: string | null
  quantity: number
  value_per_unit: number
  gross_value_per_unit: number | null
  factor: number | null
  complete_factor: number | null
  total_value: number
  net_value: number
  isin_code: string | null
  asset_issued: string | null
  related_to: string | null
  remarks: string | null
}

export interface ProventosListResponse {
  total: number
  page: number
  page_size: number
  items: ProventoItem[]
}

export interface ProventosEvolucao {
  month: string
  recebido: number
  a_receber: number
}

export const proventosService = {
  getSummary: (portfolioId: number) =>
    api.get<ProventosSummary>(`/portfolios/${portfolioId}/proventos/summary`).then(r => r.data),

  getDistribuicao: (portfolioId: number, months = 12) =>
    api.get<ProventoDistribution[]>(`/portfolios/${portfolioId}/proventos/distribuicao`, { params: { months } }).then(r => r.data),

  getHistoricoMensal: (portfolioId: number, status?: string, assetType?: string, dividendType?: string) =>
    api.get<ProventosHistoricoMes[]>(`/portfolios/${portfolioId}/proventos/historico-mensal`, {
      params: { status: status || undefined, asset_type: assetType || undefined, dividend_type: dividendType || undefined },
    }).then(r => r.data),

  getList: (
    portfolioId: number,
    params?: { status?: string; year?: number; asset_type?: string; dividend_type?: string; page?: number; page_size?: number },
  ) => api.get<ProventosListResponse>(`/portfolios/${portfolioId}/proventos`, { params }).then(r => r.data),

  sync: (portfolioId: number) =>
    api.post<{ message: string; queued: number; tickers: string[] }>(`/portfolios/${portfolioId}/dividends/sync`).then(r => r.data),
}
