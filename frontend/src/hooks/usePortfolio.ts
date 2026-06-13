import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'
import { PORTFOLIOS_QUERY_KEY } from '@/hooks/usePortfolios'

// ── Tipos ──────────────────────────────────────────────────────────────────────────────────

export interface PortfolioDetail {
  id: number
  name: string
  description: string | null
  created_at: string
}

export interface PortfolioSummaryData {
  total_invested:            number
  total_current:             number
  result_abs:                number
  result_pct:                number
  positions_count:           number
  total_patrimonio:          number
  total_investido:           number
  lucro_total:               number
  variacao_valor:            number
  variacao_percentual:       number
  rentabilidade_total:       number
  dividendos_recebidos_12m:  number
  total_proventos:           number
}

export interface PatrimonioHistoryPoint {
  month:    string
  value:    number  // capital aportado acumulado (= valor investido)
  invested: number  // alias explícito para uso no gráfico
}

export interface EquityPoint {
  date: string
  value: number
}

export type EquityPeriod = '6m' | '12m' | '24m' | 'all'

export interface AssetTypeDistribution {
  type: string
  label: string
  value: number
  percentage: number
  color: string
}

export interface PositionItem {
  id: number
  ticker: string
  name: string
  asset_type: string
  asset_label: string
  logo_url?: string
  quantity: number
  average_price: number
  current_price: number
  current_value: number
  variation_value: number
  variation_percent: number
  rentability_percent: number
  portfolio_percent: number
}

export interface PositionGroup {
  asset_type: string
  label: string
  count: number
  total_value: number
  variation_percent: number
  rentability_percent: number
  portfolio_percent: number
  positions: PositionItem[]
}

// ── Constantes ───────────────────────────────────────────────────────────────────────────────

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

const ASSET_COLORS: Record<string, string> = {
  ACAO:              '#3b82f6',
  ACAO_NACIONAL:     '#3b82f6',
  FII:               '#a855f7',
  ETF_NACIONAL:      '#14b8a6',
  STOCK:             '#0ea5e9',
  ETF_INTERNACIONAL: '#06b6d4',
  TESOURO_DIRETO:    '#eab308',
  RENDA_FIXA:        '#f97316',
  CRIPTO:            '#f43f5e',
  OUTROS:            '#6b7280',
}

// ── Helper: mapeia RawPosition -> PositionGroup[] ─────────────────────────────────────────────

interface RawPositionItem {
  ticker:         string
  asset_type:     string
  asset_label?:   string
  logo_url?:      string | null
  quantity:       number
  avg_price:      number
  total_invested: number
  current_price?: number | null
  current_value?: number | null
  result_abs?:    number | null
  result_pct?:    number | null
}

function toPositionGroups(raw: RawPositionItem[]): PositionGroup[] {
  if (!raw || raw.length === 0) return []
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
    const total_value    = items.reduce((s, p) => s + (p.current_value ?? p.total_invested ?? 0), 0)
    const total_invested = items.reduce((s, p) => s + (p.total_invested ?? 0), 0)
    const variation_value   = total_value - total_invested
    const variation_percent = total_invested > 0 ? (variation_value / total_invested) * 100 : 0
    const label = items[0]?.asset_label ?? ASSET_LABELS[asset_type] ?? asset_type
    return {
      asset_type,
      label,
      count:               items.length,
      total_value,
      variation_percent,
      rentability_percent: variation_percent,
      portfolio_percent:   grandTotal > 0 ? (total_value / grandTotal) * 100 : 0,
      positions: items.map((p, idx) => ({
        id:                  groupIdx * 1000 + idx,
        ticker:              p.ticker,
        name:                p.ticker,
        asset_type:          p.asset_type,
        asset_label:         p.asset_label ?? ASSET_LABELS[p.asset_type] ?? p.asset_type,
        logo_url:            p.logo_url ?? undefined,
        quantity:            p.quantity,
        average_price:       p.avg_price,
        current_price:       p.current_price ?? p.avg_price,
        current_value:       p.current_value ?? p.total_invested,
        variation_value:     p.result_abs  ?? 0,
        variation_percent:   p.result_pct  ?? 0,
        rentability_percent: p.result_pct  ?? 0,
        portfolio_percent:   grandTotal > 0
          ? ((p.current_value ?? p.total_invested ?? 0) / grandTotal) * 100
          : 0,
      })),
    } as PositionGroup
  }).sort((a, b) => b.total_value - a.total_value)
}

// ── Hooks ──────────────────────────────────────────────────────────────────────────────────

export function usePortfolioList() {
  return useQuery<PortfolioDetail[]>({
    queryKey: PORTFOLIOS_QUERY_KEY,
    queryFn: () => api.get('/portfolios').then(r => r.data),
    staleTime: 30_000,
  })
}

export function usePortfolio(id: number | null) {
  return useQuery<PortfolioDetail>({
    queryKey: ['portfolio', id],
    queryFn: () => api.get(`/portfolios/${id}`).then(r => r.data),
    enabled: !!id,
    staleTime: 30_000,
  })
}

export function usePortfolioSummary(portfolioId: number | null) {
  return useQuery<PortfolioSummaryData>({
    queryKey: ['portfolio-summary', portfolioId],
    queryFn: () => api.get(`/portfolios/${portfolioId}/summary`).then(r => r.data),
    enabled: !!portfolioId,
    staleTime: 15_000,
  })
}

export function useAssetDistribution(portfolioId: number | null) {
  return useQuery<AssetTypeDistribution[]>({
    queryKey: ['asset-distribution', portfolioId],
    queryFn: () =>
      api.get(`/portfolios/${portfolioId}/positions`).then(r => {
        const positions: RawPositionItem[] = r.data ?? []
        const map: Record<string, number> = {}
        for (const p of positions) {
          const t = p.asset_type ?? 'OUTROS'
          map[t] = (map[t] ?? 0) + (p.current_value ?? p.total_invested ?? 0)
        }
        const total = Object.values(map).reduce((s, v) => s + v, 0)
        return Object.entries(map).map(([asset_type, value]) => ({
          type:       asset_type,
          label:      ASSET_LABELS[asset_type] ?? asset_type,
          value,
          percentage: total > 0 ? (value / total) * 100 : 0,
          color:      ASSET_COLORS[asset_type] ?? ASSET_COLORS.OUTROS,
        })).sort((a, b) => b.value - a.value)
      }),
    enabled: !!portfolioId,
    staleTime: 15_000,
  })
}

export function usePositions(portfolioId: number | null) {
  return useQuery<PositionGroup[]>({
    queryKey: ['positions', portfolioId],
    queryFn: () =>
      api.get(`/portfolios/${portfolioId}/positions`)
        .then(r => toPositionGroups(r.data ?? [])),
    enabled: !!portfolioId,
    staleTime: 15_000,
  })
}

export function usePatrimonioHistory(portfolioId: number | null, months: number) {
  const period = months >= 60 ? 'all' : `${months}m`
  return useQuery<PatrimonioHistoryPoint[]>({
    queryKey: ['patrimonio-history', portfolioId, months],
    queryFn: () =>
      api
        .get(`/portfolios/${portfolioId}/equity-history`, { params: { period } })
        .then(r => {
          const raw: Array<{ month?: string; date?: string; value: number; invested?: number }> = r.data ?? []
          return raw.map(item => ({
            month:    item.month ?? item.date ?? '',
            value:    item.value,
            invested: item.invested ?? item.value,
          }))
        }),
    enabled: !!portfolioId,
    staleTime: 60_000,
    retry: false,
    placeholderData: [],
  })
}

export function useEquityHistory(portfolioId: number | null, period: EquityPeriod = '12m') {
  return useQuery<EquityPoint[]>({
    queryKey: ['equity-history', portfolioId, period],
    queryFn: () =>
      api
        .get(`/portfolios/${portfolioId}/equity-history`, { params: { period } })
        .then(r => r.data ?? []),
    enabled: !!portfolioId,
    staleTime: 60_000,
    retry: false,
    placeholderData: [],
  })
}
