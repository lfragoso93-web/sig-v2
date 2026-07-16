import api from './api'

export interface RentabilidadeKpis {
  patrimonio_atual:         number
  custo_total:              number
  total_aportado:           number
  ganho_nao_realizado:      number
  ganho_realizado:          number
  total_pnl:                number
  retorno_total_pct:        number
  retorno_dia_pct:          number
  retorno_mes_pct:          number
  retorno_12m_pct:          number
  retorno_desde_inicio_pct: number
  proventos_total:          number
  proventos_12m:            number
  snapshot_date:            string | null
  return_is_estimated:      boolean
  has_partial_prices:       boolean
}

export interface RentabilidadeAtivo {
  ticker:          string
  name:            string
  asset_type:      string
  quantity:        number
  avg_price:       number
  total_invested:  number
  current_value:   number
  unrealized_pnl:  number
  unrealized_pct:  number
  realized_pnl:    number
  total_pnl:       number
  total_pnl_pct:   number
  is_open:         boolean
}

export interface RentabilidadeClasse {
  asset_type:      string
  total_invested:  number
  current_value:   number
  unrealized_pnl:  number
  realized_pnl:    number
  total_pnl:       number
  total_pnl_pct:   number
  alocacao_pct:    number
  count:           number
}

export const rentabilidadeService = {
  getKpis: (portfolioId: number) =>
    api
      .get<RentabilidadeKpis>(`/portfolios/${portfolioId}/rentabilidade/kpis`)
      .then(r => r.data),

  getAtivos: (portfolioId: number) =>
    api
      .get<RentabilidadeAtivo[]>(`/portfolios/${portfolioId}/rentabilidade/ativos`)
      .then(r => r.data),

  getClasses: (portfolioId: number) =>
    api
      .get<RentabilidadeClasse[]>(`/portfolios/${portfolioId}/rentabilidade/classes`)
      .then(r => r.data),
}
