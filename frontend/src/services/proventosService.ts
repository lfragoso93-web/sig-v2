import api from './api'

// ─── Tipos alinhados com backend (proventos_service.py) ────────────────────────────────────────────

export interface ProventosSummary {
  total_recebido: number
  total_a_receber: number
  total_12m: number
  media_mensal_12m: number
}

export interface ProventoDistribution {
  ticker: string
  asset_type: string
  total: number
  percentage: number
}

export interface ProventosHistoricoMes {
  year: number
  months: (number | null)[]  // indices 0-11 = jan-dez; null = sem provento
  total: number
  media: number
}

export interface ProventoItem {
  id: number
  ticker: string
  asset_type: string
  dividend_type: string
  status: 'RECEBIDO' | 'A_RECEBER'
  ex_date: string
  payment_date: string | null
  quantity: number
  value_per_unit: number
  total_value: number
  net_value: number
}

export interface ProventosListResponse {
  total: number
  page: number
  page_size: number
  items: ProventoItem[]
}

/** Ponto de evolução mensal de proventos — usado em ProventosBarChart */
export interface ProventosEvolucao {
  month: string       // ex: 'Jan/25'
  recebido: number
  a_receber: number
}

// ─── Service ─────────────────────────────────────────────────────────────────────────────────

export const proventosService = {
  getSummary: (portfolioId: number) =>
    api
      .get<ProventosSummary>(`/portfolios/${portfolioId}/proventos/summary`)
      .then(r => r.data),

  getDistribuicao: (portfolioId: number, months = 12) =>
    api
      .get<ProventoDistribution[]>(`/portfolios/${portfolioId}/proventos/distribuicao`, {
        params: { months },
      })
      .then(r => r.data),

  getHistoricoMensal: (portfolioId: number, status?: string, assetType?: string) =>
    api
      .get<ProventosHistoricoMes[]>(`/portfolios/${portfolioId}/proventos/historico-mensal`, {
        params: {
          status:     status     || undefined,
          asset_type: assetType  || undefined,
        },
      })
      .then(r => r.data),

  getList: (
    portfolioId: number,
    params?: {
      status?:     string
      year?:       number
      asset_type?: string
      page?:       number
      page_size?:  number
    },
  ) =>
    api
      .get<ProventosListResponse>(`/portfolios/${portfolioId}/proventos`, { params })
      .then(r => r.data),

  sync: (portfolioId: number) =>
    api
      .post<{ message: string; queued: number; tickers: string[] }>(
        `/portfolios/${portfolioId}/dividends/sync`,
      )
      .then(r => r.data),
}
