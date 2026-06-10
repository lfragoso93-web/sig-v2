import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'

// ── tipos base ──────────────────────────────────────────────────────────────
export interface PortfolioDetail {
  id: number
  name: string
  description: string | null
  created_at: string
}

export interface PortfolioSummaryData {
  total_invested:           number
  total_current:            number
  result_abs:               number
  result_pct:               number
  positions_count:          number
  total_patrimonio:         number
  total_investido:          number
  lucro_total:              number
  variacao_valor:           number
  variacao_percentual:      number
  rentabilidade_total:      number
  dividendos_recebidos_12m: number
  total_proventos:          number
  // alias extra usado em ResumePage
  ganho_capital?:           number
}

export interface AssetDistributionItem {
  asset_type: string
  label:      string
  value:      number
  pct:        number
}

export interface PositionItem {
  ticker:        string
  asset_type:    string
  quantity:      number
  avg_price:     number
  total_invested: number
  current_price?: number | null
  current_value?: number | null
  result_abs?:    number | null
  result_pct?:    number | null
}

export interface PositionGroup {
  label:  string
  count:  number
  items:  PositionItem[]
}

export interface PatrimonioHistoryPoint {
  month:  string
  value:  number
}

// ── hooks ───────────────────────────────────────────────────────────────

export function usePortfolioList() {
  return useQuery<PortfolioDetail[]>({
    queryKey: ['portfolios'],
    queryFn: () => api.get('/portfolios/').then(r => r.data),
  })
}

export function usePortfolio(id: number | null) {
  return useQuery<PortfolioDetail>({
    queryKey: ['portfolio', id],
    queryFn: () => api.get(`/portfolios/${id}`).then(r => r.data),
    enabled: !!id,
  })
}

/**
 * Resumo financeiro — endpoint: GET /portfolios/{id}/summary
 * Retorna todos os campos já normalizados pelo backend.
 */
export function usePortfolioSummary(portfolioId: number | null) {
  return useQuery<PortfolioSummaryData>({
    queryKey: ['portfolio-summary', portfolioId],
    queryFn: () =>
      api
        .get(`/portfolios/${portfolioId}/summary`)
        .then(r => ({
          ...r.data,
          ganho_capital: r.data.lucro_total ?? 0,
        })),
    enabled: !!portfolioId,
  })
}

/**
 * Distribuição de ativos — calculada no frontend a partir de /positions
 */
export function useAssetDistribution(portfolioId: number | null) {
  return useQuery<AssetDistributionItem[]>({
    queryKey: ['asset-distribution', portfolioId],
    queryFn: () =>
      api
        .get(`/portfolios/${portfolioId}/positions`)
        .then(r => {
          const positions: PositionItem[] = r.data
          const map: Record<string, number> = {}
          for (const p of positions) {
            const t = p.asset_type ?? 'OUTROS'
            map[t] = (map[t] ?? 0) + (p.current_value ?? p.total_invested ?? 0)
          }
          const total = Object.values(map).reduce((s, v) => s + v, 0)
          const LABELS: Record<string, string> = {
            ACAO: 'Ações', FII: 'FIIs', ETF_NACIONAL: 'ETFs BR',
            STOCK: 'Stocks', ETF_INTERNACIONAL: 'ETFs INT',
            TESOURO_DIRETO: 'Tesouro', RENDA_FIXA: 'Renda Fixa', CRIPTO: 'Cripto',
          }
          return Object.entries(map).map(([asset_type, value]) => ({
            asset_type,
            label: LABELS[asset_type] ?? asset_type,
            value,
            pct: total > 0 ? (value / total) * 100 : 0,
          })).sort((a, b) => b.value - a.value)
        }),
    enabled: !!portfolioId,
  })
}

/**
 * Posições agrupadas por tipo — endpoint: GET /portfolios/{id}/positions
 */
export function usePositions(portfolioId: number | null) {
  return useQuery<PositionGroup[]>({
    queryKey: ['positions', portfolioId],
    queryFn: () =>
      api
        .get(`/portfolios/${portfolioId}/positions`)
        .then(r => {
          const positions: PositionItem[] = r.data
          const grouped: Record<string, PositionItem[]> = {}
          for (const p of positions) {
            const t = p.asset_type ?? 'OUTROS'
            if (!grouped[t]) grouped[t] = []
            grouped[t].push(p)
          }
          const LABELS: Record<string, string> = {
            ACAO: 'Ações', FII: 'FIIs', ETF_NACIONAL: 'ETFs BR',
            STOCK: 'Stocks', ETF_INTERNACIONAL: 'ETFs INT',
            TESOURO_DIRETO: 'Tesouro Direto', RENDA_FIXA: 'Renda Fixa', CRIPTO: 'Cripto',
          }
          return Object.entries(grouped).map(([type, items]) => ({
            label: LABELS[type] ?? type,
            count: items.length,
            items,
          })).sort((a, b) =>
            b.items.reduce((s, i) => s + (i.current_value ?? i.total_invested ?? 0), 0) -
            a.items.reduce((s, i) => s + (i.current_value ?? i.total_invested ?? 0), 0)
          )
        }),
    enabled: !!portfolioId,
  })
}

/**
 * Histórico mensal — endpoint ainda não existe, retorna vazio
 */
export function usePatrimonioHistory(portfolioId: number | null, _months: number) {
  return useQuery<PatrimonioHistoryPoint[]>({
    queryKey: ['patrimonio-history', portfolioId, _months],
    queryFn: () => Promise.resolve([]),
    enabled: !!portfolioId,
  })
}
