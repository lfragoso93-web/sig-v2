import api from './api'

export interface ProventosSummary {
  media_mensal: number
  meta_mensal: number
  meta_percent: number
  total_12m: number
  total_carteira: number
}

export interface ProventoDistribution {
  ticker: string
  total: number
  percentage: number
  color?: string
}

export interface ProventosEvolucao {
  month: string
  recebido: number
  a_receber: number
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
  status: 'RECEBIDO' | 'A_RECEBER'
  ex_date: string
  payment_date: string | null
  quantity: number
  value_per_unit: number
  total_value: number
  net_value: number
}

export const proventosService = {
  getSummary: (portfolioId: number) =>
    api.get<ProventosSummary>(`/api/v1/portfolios/${portfolioId}/proventos/summary`).then(r => r.data),

  getDistribution: (portfolioId: number, months = 12) =>
    api.get<ProventoDistribution[]>(`/api/v1/portfolios/${portfolioId}/proventos/distribution`, { params: { months } }).then(r => r.data),

  getEvolucao: (portfolioId: number, tipo: 'mensal' | 'anual', period: string) =>
    api.get<ProventosEvolucao[]>(`/api/v1/portfolios/${portfolioId}/proventos/evolucao`, { params: { tipo, period } }).then(r => r.data),

  getHistoricoMensal: (portfolioId: number, status: string, assetType: string) =>
    api.get<ProventosHistoricoMes[]>(`/api/v1/portfolios/${portfolioId}/proventos/historico-mensal`, { params: { status, asset_type: assetType } }).then(r => r.data),

  getList: (portfolioId: number, year?: number, status?: string, assetType?: string) =>
    api.get<ProventoItem[]>(`/api/v1/portfolios/${portfolioId}/proventos`, { params: { year, status, asset_type: assetType } }).then(r => r.data),
}
