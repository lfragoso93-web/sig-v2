import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'

// ── tipos base ────────────────────────────────────────────────────────────────
export interface PortfolioDetail {
  id: number
  name: string
  description: string | null
  created_at: string
}

export interface PortfolioSummaryData {
  total_invested:     number
  total_current:      number
  result_abs:         number
  result_pct:         number
  positions_count:    number
  // aliases usados no ResumePage / PatrimonioPage
  total_patrimonio?:  number
  total_investido?:   number
  lucro_total?:       number
  variacao_valor?:    number
  variacao_percentual?: number
  rentabilidade_total?: number
  dividendos_recebidos_12m?: number
  total_proventos?:   number
}

export interface AssetDistributionItem {
  asset_type: string
  label:      string
  value:      number
  pct:        number
}

export interface PositionItem {
  id:            number
  ticker:        string
  asset_type:    string
  quantity:      number
  avg_price:     number
  current_price: number
  current_value: number
  result_abs:    number
  result_pct:    number
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

// ── hooks ────────────────────────────────────────────────────────────────────

/** Lista todas as carteiras do usuário */
export function usePortfolioList() {
  return useQuery<PortfolioDetail[]>({
    queryKey: ['portfolios'],
    queryFn: () => api.get('/portfolios').then(r => r.data),
  })
}

/** Detalhe de uma carteira específica */
export function usePortfolio(id: number | null) {
  return useQuery<PortfolioDetail>({
    queryKey: ['portfolio', id],
    queryFn: () => api.get(`/portfolios/${id}`).then(r => r.data),
    enabled: !!id,
  })
}

/**
 * Resumo financeiro da carteira.
 * O backend retorna total_invested / total_current / result_abs / result_pct.
 * Aqui normalizamos para os nomes usados nas páginas.
 */
export function usePortfolioSummary(portfolioId: number) {
  return useQuery<PortfolioSummaryData>({
    queryKey: ['portfolio-summary', portfolioId],
    queryFn: () =>
      api
        .get(`/portfolios/${portfolioId}/positions/summary`)
        .then(r => {
          const d = r.data
          return {
            ...d,
            // normaliza nomes para as páginas
            total_patrimonio:        d.total_current   ?? 0,
            total_investido:         d.total_invested  ?? 0,
            lucro_total:             d.result_abs      ?? 0,
            variacao_valor:          d.result_abs      ?? 0,
            variacao_percentual:     d.result_pct      ?? 0,
            rentabilidade_total:     d.result_pct      ?? 0,
            dividendos_recebidos_12m: d.dividendos_recebidos_12m ?? 0,
            total_proventos:         d.total_proventos ?? 0,
          } as PortfolioSummaryData
        }),
    enabled: !!portfolioId,
  })
}

/**
 * Distribuição de ativos por tipo para o donut chart.
 * Calculado no frontend a partir das posições, sem endpoint dedicado.
 */
export function useAssetDistribution(portfolioId: number) {
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
            map[t] = (map[t] ?? 0) + (p.current_value ?? p.avg_price * p.quantity)
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
 * Posições agrupadas por tipo de ativo.
 * O backend retorna lista plana; aqui agrupamos para o PositionTable.
 */
export function usePositions(portfolioId: number) {
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
          })).sort((a, b) => b.items.reduce((s, i) => s + (i.current_value ?? 0), 0)
                              - a.items.reduce((s, i) => s + (i.current_value ?? 0), 0))
        }),
    enabled: !!portfolioId,
  })
}

/**
 * Histórico de patrimônio mensal.
 * Endpoint ainda não existe no backend — retorna array vazio até ser implementado.
 */
export function usePatrimonioHistory(portfolioId: number, _months: number) {
  return useQuery<PatrimonioHistoryPoint[]>({
    queryKey: ['patrimonio-history', portfolioId, _months],
    queryFn: () => Promise.resolve([]),   // TODO: implementar endpoint
    enabled: !!portfolioId,
  })
}
