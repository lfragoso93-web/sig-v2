import { useMemo, useState } from 'react'
import { TrendingUp, TrendingDown, BarChart2, RefreshCw, Wallet } from 'lucide-react'
import clsx from 'clsx'
import {
  usePortfolioSummary,
  useAssetDistribution,
  usePositions,
  type PositionGroup,
} from '@/hooks/usePortfolio'
import { useAppStore } from '@/store/appStore'
import { formatBRL, formatPercent, signClass } from '@/utils/format'
import KpiCard from '@/components/ui/KpiCard'
import SkeletonCard from '@/components/ui/SkeletonCard'
import EmptyState from '@/components/ui/EmptyState'
import AssetDonutChart from '@/components/charts/AssetDonutChart'
import PositionTable from '@/components/resume/PositionTable'

const ASSET_TYPE_LABELS: Record<string, string> = {
  ACAO: 'Ações', ACAO_NACIONAL: 'Ações', FII: 'FIIs',
  ETF_NACIONAL: 'ETFs BR', STOCK: 'Stocks', ETF_INTERNACIONAL: 'ETFs INT',
  TESOURO_DIRETO: 'Tesouro Direto', RENDA_FIXA: 'Renda Fixa', CRIPTO: 'Cripto',
}

// Cores semanticas usando tokens CSS — funcionam em light e dark
const ASSET_TYPE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  ACAO:              { bg: 'var(--color-blue-highlight)',   text: 'var(--color-blue)',   border: 'var(--color-blue-highlight)' },
  ACAO_NACIONAL:     { bg: 'var(--color-blue-highlight)',   text: 'var(--color-blue)',   border: 'var(--color-blue-highlight)' },
  FII:               { bg: 'var(--color-purple-highlight)', text: 'var(--color-purple)', border: 'var(--color-purple-highlight)' },
  ETF_NACIONAL:      { bg: 'var(--color-primary-highlight)',text: 'var(--color-primary)',border: 'var(--color-primary-highlight)' },
  STOCK:             { bg: 'var(--color-blue-highlight)',   text: 'var(--color-blue)',   border: 'var(--color-blue-highlight)' },
  ETF_INTERNACIONAL: { bg: 'var(--color-blue-highlight)',   text: 'var(--color-blue)',   border: 'var(--color-blue-highlight)' },
  TESOURO_DIRETO:    { bg: 'var(--color-gold-highlight)',   text: 'var(--color-gold)',   border: 'var(--color-gold-highlight)' },
  RENDA_FIXA:        { bg: 'var(--color-orange-highlight)', text: 'var(--color-orange)', border: 'var(--color-orange-highlight)' },
  CRIPTO:            { bg: 'var(--color-error-highlight)',  text: 'var(--color-error)',  border: 'var(--color-error-highlight)' },
}
const FALLBACK_COLOR = { bg: 'var(--color-surface-dynamic)', text: 'var(--color-text-muted)', border: 'var(--color-border)' }

export default function PatrimonioPage() {
  const portfolioId = useAppStore(s => s.selectedPortfolioId)
  const [activeTypeFilter, setActiveTypeFilter] = useState<string | null>(null)

  const { data: summary,      isLoading: loadingSummary  } = usePortfolioSummary(portfolioId)
  const { data: distribution, isLoading: loadingDist     } = useAssetDistribution(portfolioId)
  const { data: positions,    isLoading: loadingPositions } = usePositions(portfolioId)

  const allPositions = useMemo(() => {
    if (!positions) return []
    return positions.flatMap((g: PositionGroup) => g.positions ?? [])
  }, [positions])

  const typeBreakdown = useMemo(() => {
    const map: Record<string, { total: number; count: number }> = {}
    for (const p of allPositions) {
      const t = p.asset_type ?? 'OUTROS'
      if (!map[t]) map[t] = { total: 0, count: 0 }
      map[t].total += p.current_value ?? 0
      map[t].count += 1
    }
    const grandTotal = Object.values(map).reduce((s, v) => s + v.total, 0)
    return Object.entries(map)
      .map(([type, { total, count }]) => ({ type, total, count, pct: grandTotal > 0 ? (total / grandTotal) * 100 : 0 }))
      .sort((a, b) => b.total - a.total)
  }, [allPositions])

  const filteredPositions = useMemo(() => {
    if (!positions) return []
    if (!activeTypeFilter) return positions
    return positions
      .map((g: PositionGroup) => ({ ...g, positions: g.positions.filter(p => p.asset_type === activeTypeFilter) }))
      .filter((g: PositionGroup) => g.positions.length > 0)
  }, [positions, activeTypeFilter])

  if (!portfolioId) {
    return (
      <div className="p-6">
        <EmptyState icon={Wallet} title="Nenhuma carteira selecionada" description="Selecione uma carteira no menu superior para visualizar o patrimônio." />
      </div>
    )
  }

  return (
    <div className="px-4 py-5 max-w-screen-xl mx-auto flex flex-col gap-5">

      {/* Cabeçalho */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-base font-semibold">Patrimônio</h1>
          <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>Visão consolidada dos ativos da carteira selecionada</p>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {loadingSummary ? (
          [...Array(4)].map((_, i) => <SkeletonCard key={i} />)
        ) : summary ? (
          <>
            <KpiCard label="Patrimônio Total" value={formatBRL(summary.total_patrimonio ?? 0)} subValue={formatBRL(summary.total_investido ?? 0)} subLabel="Valor investido" change={summary.variacao_percentual} />
            <KpiCard label="Resultado" value={formatBRL(summary.lucro_total ?? 0)} subLabel="Ganho de capital + proventos" />
            <KpiCard label="Proventos (12m)" value={formatBRL(summary.dividendos_recebidos_12m ?? 0)} subValue={formatBRL(summary.total_proventos ?? 0)} subLabel="Total recebido" />
            <div className="rounded-xl p-4 flex flex-col gap-1" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
              <span className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>Variação</span>
              <div className={clsx('text-xl font-bold tabular-nums tracking-tight', signClass(summary.variacao_valor ?? 0))}>
                {formatBRL(summary.variacao_valor ?? 0)}
              </div>
              <div className={clsx('text-xs font-medium flex items-center gap-1', signClass(summary.variacao_valor ?? 0))}>
                {(summary.variacao_valor ?? 0) >= 0 ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                {formatPercent(summary.variacao_percentual ?? 0)}
              </div>
              <div className={clsx('text-sm font-bold mt-1 tabular-nums', signClass(summary.rentabilidade_total ?? 0))}>
                {formatPercent(summary.rentabilidade_total ?? 0)}
                <span className="text-xs font-normal ml-1" style={{ color: 'var(--color-text-muted)' }}>rentab.</span>
              </div>
            </div>
          </>
        ) : (
          <div className="col-span-4 py-8 text-center text-xs" style={{ color: 'var(--color-text-muted)' }}>
            Nenhum dado disponível. Adicione lançamentos para começar.
          </div>
        )}
      </div>

      {/* Breakdown por classe + donut */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 rounded-xl overflow-hidden" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
          <div className="flex items-center gap-2 px-4 py-3" style={{ borderBottom: '1px solid var(--color-divider)' }}>
            <BarChart2 size={15} style={{ color: 'var(--color-primary)' }} />
            <span className="text-xs font-semibold">Alocação por Classe</span>
          </div>
          {loadingPositions ? (
            <div className="p-4 flex flex-col gap-2">
              {[...Array(5)].map((_, i) => <div key={i} className="h-10 rounded skeleton" />)}
            </div>
          ) : typeBreakdown.length === 0 ? (
            <div className="py-10 text-center text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Nenhum ativo encontrado. Adicione lançamentos para visualizar sua alocação.
            </div>
          ) : (
            <div style={{ borderTop: 'none' }}>
              {typeBreakdown.map(({ type, total, count, pct }) => {
                const clr = ASSET_TYPE_COLORS[type] ?? FALLBACK_COLOR
                const isActive = activeTypeFilter === type
                return (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setActiveTypeFilter(isActive ? null : type)}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left transition-colors duration-150"
                    style={{
                      background: isActive ? 'var(--color-surface-offset)' : 'transparent',
                      borderBottom: '1px solid var(--color-divider)',
                    }}
                    onMouseEnter={e => !isActive && (e.currentTarget.style.background = 'var(--color-surface-offset-2)')}
                    onMouseLeave={e => !isActive && (e.currentTarget.style.background = 'transparent')}
                  >
                    <span
                      className="shrink-0 text-xs font-medium px-2 py-0.5 rounded border"
                      style={{ background: clr.bg, color: clr.text, borderColor: clr.border }}
                    >
                      {ASSET_TYPE_LABELS[type] ?? type}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--color-surface-dynamic)' }}>
                        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: 'var(--color-primary)' }} />
                      </div>
                    </div>
                    <span className="shrink-0 text-xs tabular-nums font-medium" style={{ color: 'var(--color-text)' }}>{formatBRL(total)}</span>
                    <span className="shrink-0 text-xs tabular-nums w-12 text-right" style={{ color: 'var(--color-text-muted)' }}>{pct.toFixed(1)}%</span>
                    <span className="shrink-0 text-xs w-16 text-right" style={{ color: 'var(--color-text-faint)' }}>{count} ativo{count !== 1 ? 's' : ''}</span>
                  </button>
                )
              })}
            </div>
          )}
          {activeTypeFilter && (
            <div className="px-4 py-2 flex items-center justify-between" style={{ borderTop: '1px solid var(--color-divider)' }}>
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                Mostrando apenas: <span className="font-medium" style={{ color: 'var(--color-text)' }}>{ASSET_TYPE_LABELS[activeTypeFilter] ?? activeTypeFilter}</span>
              </span>
              <button onClick={() => setActiveTypeFilter(null)} className="text-xs flex items-center gap-1" style={{ color: 'var(--color-primary)' }}>
                <RefreshCw size={11} /> Ver todos
              </button>
            </div>
          )}
        </div>

        {/* Donut */}
        <div className="rounded-xl overflow-hidden" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
          <div className="flex items-center gap-2 px-4 py-3" style={{ borderBottom: '1px solid var(--color-divider)' }}>
            <span className="text-xs font-semibold">Distribuição</span>
          </div>
          {loadingDist ? (
            <div className="h-52 flex items-center justify-center">
              <div className="skeleton w-32 h-32 rounded-full" />
            </div>
          ) : distribution && distribution.length > 0 ? (
            <AssetDonutChart data={distribution} />
          ) : (
            <div className="h-52 flex items-center justify-center text-xs" style={{ color: 'var(--color-text-muted)' }}>Sem dados</div>
          )}
        </div>
      </div>

      {/* Tabela de posições */}
      <div className="rounded-xl overflow-hidden" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
        <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: '1px solid var(--color-divider)' }}>
          <span className="text-xs font-semibold">Posições</span>
          <div className="flex items-center gap-2">
            <span
              className="ml-1 px-1.5 py-0.5 rounded text-xs tabular-nums"
              style={{ background: 'var(--color-surface-dynamic)', color: 'var(--color-text-muted)' }}
            >
              {filteredPositions.reduce((s: number, g: PositionGroup) => s + g.count, 0)}
            </span>
            {activeTypeFilter && (
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                Filtrado por: <span className="font-medium" style={{ color: 'var(--color-text)' }}>{ASSET_TYPE_LABELS[activeTypeFilter] ?? activeTypeFilter}</span>
              </span>
            )}
          </div>
        </div>
        {loadingPositions ? (
          <div className="p-4 flex flex-col gap-2">
            {[...Array(4)].map((_, i) => <div key={i} className="h-12 rounded skeleton" />)}
          </div>
        ) : (
          <PositionTable groups={filteredPositions} />
        )}
      </div>
    </div>
  )
}
