import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'
import type { PositionGroup, AssetTypeDistribution } from '@/services/portfolioService'

// ── tipos extras usados nos hooks ─────────────────────────────────────

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
  ganho_capital?:           number
}

export interface PatrimonioHistoryPoint {
  month:  string
  value:  number
}

// raw item devolvido pelo novo endpoint
interface RawPositionItem {
  ticker:         string
  asset_type:     string
  quantity:       number
  avg_price:      number
  total_invested: number
  current_price?: number | null
  current_value?: number | null
  result_abs?:    number | null
  result_pct?:    number | null
}

// ── helpers ──────────────────────────────────────────────────────────────

const ASSET_LABELS: Record<string, string> = {
  ACAO:              'Ações',
  ACAO_NACIONAL:     'Ações',
  FII:               'FIIs',
  ETF_NACIONAL:      'ETFs Nacionais',
  STOCK:             'Stocks',
  ETF_INTERNACIONAL: 'ETFs Internacionais',
  TESOURO_DIRETO:    'Tesouro Direto',
  RENDA_FIXA:        'Renda Fixa',
  CRIPTO:            'Criptomoedas',
}

/** Converte lista flat de RawPositionItem → PositionGroup[] (schema do PositionTable) */
function toPositionGroups(raw: RawPositionItem[]): PositionGroup[] {
  const byType: Record<string, RawPositionItem[]> = {}
  for (const p of raw) {
    const t = p.asset_type ?? 'OUTROS'
    if (!byType[t]) byType[t] = []
    byType[t].push(p)
  }

  const grandTotal = raw.reduce(
    (s, p) => s + (p.current_value ?? p.total_invested ?? 0), 0
  )

  return Object.entries(byType).map(([asset_type, items], groupIdx) => {
    const total_value = items.reduce(
      (s, p) => s + (p.current_value ?? p.total_invested ?? 0), 0
    )
    const total_invested = items.reduce((s, p) => s + (p.total_invested ?? 0), 0)
    const variation_value  = total_value - total_invested
    const variation_percent  = total_invested > 0
      ? (variation_value / total_invested) * 100 : 0

    return {
      asset_type,
      label:               ASSET_LABELS[asset_type] ?? asset_type,
      count:               items.length,
      total_value,
      variation_percent,
      rentability_percent: variation_percent,
      portfolio_percent:   grandTotal > 0 ? (total_value / grandTotal) * 100 : 0,
      // mapeia para o schema de PositionItem que PositionTable usa
      positions: items.map((p, idx) => ({
        id:                  groupIdx * 1000 + idx,
        ticker:              p.ticker,
        name:                p.ticker,          // sem nome detalhado por ora
        asset_type:          p.asset_type,
        logo_url:            undefined,
        quantity:            p.quantity,
        average_price:       p.avg_price,
        current_price:       p.current_price ?? p.avg_price,
        current_value:       p.current_value ?? p.total_invested,
        variation_value:     (p.result_abs ?? 0),
        variation_percent:   (p.result_pct ?? 0),
        rentability_percent: (p.result_pct ?? 0),
        portfolio_percent:   grandTotal > 0
          ? ((p.current_value ?? p.total_invested ?? 0) / grandTotal) * 100
          : 0,
      })),
    } as PositionGroup
  }).sort((a, b) => b.total_value - a.total_value)
}

// ── hooks ──────────────────────────────────────────────────────────────

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

/** Resumo financeiro — GET /portfolios/{id}/summary */
export function usePortfolioSummary(portfolioId: number | null) {
  return useQuery<PortfolioSummaryData>({
    queryKey: ['portfolio-summary', portfolioId],
    queryFn: () =>
      api
        .get(`/portfolios/${portfolioId}/summary`)
        .then(r => ({ ...r.data, ganho_capital: r.data.lucro_total ?? 0 })),
    enabled: !!portfolioId,
  })
}

/** Distribuição de ativos — calculada a partir de /positions */
export function useAssetDistribution(portfolioId: number | null) {
  return useQuery<AssetTypeDistribution[]>({
    queryKey: ['asset-distribution', portfolioId],
    queryFn: () =>
      api
        .get(`/portfolios/${portfolioId}/positions`)
        .then(r => {
          const positions: RawPositionItem[] = r.data
          const map: Record<string, number> = {}
          for (const p of positions) {
            const t = p.asset_type ?? 'OUTROS'
            map[t] = (map[t] ?? 0) + (p.current_value ?? p.total_invested ?? 0)
          }
          const total = Object.values(map).reduce((s, v) => s + v, 0)
          const COLORS: Record<string, string> = {
            ACAO: '#3b82f6', FII: '#a855f7', ETF_NACIONAL: '#14b8a6',
            STOCK: '#0ea5e9', ETF_INTERNACIONAL: '#06b6d4',
            TESOURO_DIRETO: '#eab308', RENDA_FIXA: '#f97316',
            CRIPTO: '#f43f5e', OUTROS: '#6b7280',
          }
          return Object.entries(map).map(([asset_type, value]) => ({
            type:       asset_type,
            label:      ASSET_LABELS[asset_type] ?? asset_type,
            value,
            percentage: total > 0 ? (value / total) * 100 : 0,
            color:      COLORS[asset_type] ?? '#6b7280',
          })).sort((a, b) => b.value - a.value)
        }),
    enabled: !!portfolioId,
  })
}

/** Posições agrupadas por tipo — GET /portfolios/{id}/positions */
export function usePositions(portfolioId: number | null) {
  return useQuery<PositionGroup[]>({
    queryKey: ['positions', portfolioId],
    queryFn: () =>
      api
        .get(`/portfolios/${portfolioId}/positions`)
        .then(r => toPositionGroups(r.data)),
    enabled: !!portfolioId,
  })
}

/** Histórico mensal — endpoint ainda não implementado; retorna lista vazia */
export function usePatrimonioHistory(portfolioId: number | null, _months: number) {
  return useQuery<PatrimonioHistoryPoint[]>({
    queryKey: ['patrimonio-history', portfolioId, _months],
    queryFn: () => Promise.resolve([]),
    enabled: !!portfolioId,
  })
}
