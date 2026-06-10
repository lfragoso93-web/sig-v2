import { useMemo, useState } from 'react'
import {
  Wallet, TrendingUp, TrendingDown, BarChart2,
  Activity, DollarSign, RefreshCw, PackageOpen,
} from 'lucide-react'
import clsx from 'clsx'
import {
  usePortfolioList,
  usePortfolioSummary,
  useAssetDistribution,
  usePositions,
} from '@/hooks/usePortfolio'
import { formatBRL, formatPercent, signClass } from '@/utils/format'
import KpiCard from '@/components/ui/KpiCard'
import SkeletonCard from '@/components/ui/SkeletonCard'
import EmptyState from '@/components/ui/EmptyState'
import AssetDonutChart from '@/components/charts/AssetDonutChart'
import PositionTable from '@/components/resume/PositionTable'

const ASSET_TYPE_LABELS: Record<string, string> = {
  ACAO:              'Ações',
  FII:               'FIIs',
  ETF_NACIONAL:      'ETFs BR',
  STOCK:             'Stocks',
  ETF_INTERNACIONAL: 'ETFs INT',
  TESOURO_DIRETO:    'Tesouro Direto',
  RENDA_FIXA:        'Renda Fixa',
  CRIPTO:            'Cripto',
}

const ASSET_TYPE_COLORS: Record<string, string> = {
  ACAO:              'bg-blue-500/15 text-blue-400 border-blue-500/30',
  FII:               'bg-purple-500/15 text-purple-400 border-purple-500/30',
  ETF_NACIONAL:      'bg-teal-500/15 text-teal-400 border-teal-500/30',
  STOCK:             'bg-sky-500/15 text-sky-400 border-sky-500/30',
  ETF_INTERNACIONAL: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
  TESOURO_DIRETO:    'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
  RENDA_FIXA:        'bg-orange-500/15 text-orange-400 border-orange-500/30',
  CRIPTO:            'bg-rose-500/15 text-rose-400 border-rose-500/30',
}

export default function PatrimonioPage() {
  const { data: portfolios, isLoading: loadingPortfolios } = usePortfolioList()
  const [selectedPortfolio, setSelectedPortfolio] = useState<number | null>(null)
  const [activeTypeFilter, setActiveTypeFilter] = useState<string | null>(null)

  const portfolioId = selectedPortfolio ?? (portfolios?.[0]?.id ?? 0)

  const { data: summary, isLoading: loadingSummary }    = usePortfolioSummary(portfolioId)
  const { data: distribution, isLoading: loadingDist }  = useAssetDistribution(portfolioId)
  const { data: positions, isLoading: loadingPositions } = usePositions(portfolioId)

  // ── agrupa posições por tipo ─────────────────────────────────────────────
  const allPositions = useMemo(() => {
    if (!positions) return []
    return positions.flatMap((g: any) => g.items ?? [])
  }, [positions])

  const typeBreakdown = useMemo(() => {
    const map: Record<string, { total: number; count: number }> = {}
    for (const p of allPositions) {
      const t = p.asset_type ?? 'OUTROS'
      if (!map[t]) map[t] = { total: 0, count: 0 }
      map[t].total  += p.current_value ?? 0
      map[t].count  += 1
    }
    const grandTotal = Object.values(map).reduce((s, v) => s + v.total, 0)
    return Object.entries(map)
      .map(([type, { total, count }]) => ({
        type,
        total,
        count,
        pct: grandTotal > 0 ? (total / grandTotal) * 100 : 0,
      }))
      .sort((a, b) => b.total - a.total)
  }, [allPositions])

  const filteredPositions = useMemo(() => {
    if (!positions) return []
    if (!activeTypeFilter) return positions
    return positions
      .map((g: any) => ({
        ...g,
        items: (g.items ?? []).filter((p: any) => p.asset_type === activeTypeFilter),
      }))
      .filter((g: any) => g.items.length > 0)
  }, [positions, activeTypeFilter])

  // ── loading inicial ──────────────────────────────────────────────────────
  if (loadingPortfolios) {
    return (
      <div className="p-6 grid grid-cols-2 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
      </div>
    )
  }

  if (!portfolios?.length) {
    return (
      <div className="p-6">
        <EmptyState
          icon={PackageOpen}
          title="Nenhuma carteira encontrada"
          description="Crie sua primeira carteira para começar a acompanhar seu patrimônio."
        />
      </div>
    )
  }

  return (
    <div className="px-4 py-5 max-w-screen-xl mx-auto flex flex-col gap-5">

      {/* ── cabeçalho ──────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-base font-semibold text-slate-100">Patrimônio</h1>
          <p className="text-xs text-slate-500 mt-0.5">Visão consolidada de todos os seus ativos</p>
        </div>

        {/* seletor de carteira */}
        {portfolios.length > 1 && (
          <div className="flex items-center gap-1.5 flex-wrap">
            {portfolios.map(p => (
              <button
                key={p.id}
                onClick={() => setSelectedPortfolio(p.id)}
                className={clsx(
                  'px-3 py-1.5 rounded-md text-xs font-medium transition-colors duration-150',
                  portfolioId === p.id
                    ? 'bg-brand-600 text-white'
                    : 'bg-surface-800 border border-surface-600 text-slate-400 hover:bg-surface-700 hover:text-slate-200',
                )}
              >
                {p.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── KPIs ─────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {loadingSummary ? (
          [...Array(4)].map((_, i) => <SkeletonCard key={i} />)
        ) : summary ? (
          <>
            <KpiCard
              label="Patrimônio Total"
              value={formatBRL(summary.total_patrimonio)}
              subValue={formatBRL(summary.total_investido)}
              subLabel="Valor investido"
              change={summary.variacao_percentual}
            />
            <KpiCard
              label="Resultado"
              value={formatBRL(summary.lucro_total)}
              subLabel="Ganho de capital + proventos"
            />
            <KpiCard
              label="Proventos (12m)"
              value={formatBRL(summary.dividendos_recebidos_12m)}
              subValue={formatBRL(summary.total_proventos)}
              subLabel="Total recebido"
            />
            <div className="rounded-xl bg-surface-900 border border-surface-700 p-4 flex flex-col gap-1">
              <span className="text-xs text-slate-500 font-medium">Variação</span>
              <div className={clsx('text-xl font-bold tabular-nums tracking-tight', signClass(summary.variacao_valor))}>
                {formatBRL(summary.variacao_valor)}
              </div>
              <div className={clsx('text-xs font-medium flex items-center gap-1', signClass(summary.variacao_valor))}>
                {summary.variacao_valor >= 0
                  ? <TrendingUp size={11} />
                  : <TrendingDown size={11} />}
                {formatPercent(summary.variacao_percentual)}
              </div>
              <div className={clsx('text-sm font-bold mt-1 tabular-nums', signClass(summary.rentabilidade_total))}>
                {formatPercent(summary.rentabilidade_total)}
                <span className="text-xs font-normal text-slate-500 ml-1">rentab.</span>
              </div>
            </div>
          </>
        ) : null}
      </div>

      {/* ── breakdown por classe + donut ─────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Tabela de classes */}
        <div className="lg:col-span-2 rounded-xl bg-surface-900 border border-surface-700 overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-surface-700">
            <BarChart2 size={15} className="text-brand-500" />
            <span className="text-xs font-semibold text-slate-200">Alocação por Classe</span>
          </div>
          {loadingPositions ? (
            <div className="p-4 flex flex-col gap-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-10 rounded bg-surface-800 animate-pulse" />
              ))}
            </div>
          ) : typeBreakdown.length === 0 ? (
            <div className="py-10 text-center text-xs text-slate-500">Nenhum ativo encontrado</div>
          ) : (
            <div className="divide-y divide-surface-700">
              {typeBreakdown.map(({ type, total, count, pct }) => {
                const colorCls = ASSET_TYPE_COLORS[type] ?? 'bg-slate-500/15 text-slate-400 border-slate-500/30'
                const isActive = activeTypeFilter === type
                return (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setActiveTypeFilter(isActive ? null : type)}
                    className={clsx(
                      'w-full flex items-center gap-3 px-4 py-3 text-left transition-colors duration-150',
                      isActive ? 'bg-surface-800' : 'hover:bg-surface-800/60',
                    )}
                  >
                    {/* badge */}
                    <span className={clsx('shrink-0 text-xs font-medium px-2 py-0.5 rounded border', colorCls)}>
                      {ASSET_TYPE_LABELS[type] ?? type}
                    </span>

                    {/* barra */}
                    <div className="flex-1 min-w-0">
                      <div className="h-1.5 rounded-full bg-surface-700 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-brand-500 transition-all duration-500"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>

                    {/* valores */}
                    <span className="shrink-0 text-xs tabular-nums font-medium text-slate-300">
                      {formatBRL(total)}
                    </span>
                    <span className="shrink-0 text-xs tabular-nums text-slate-500 w-12 text-right">
                      {pct.toFixed(1)}%
                    </span>
                    <span className="shrink-0 text-xs text-slate-600 w-16 text-right">
                      {count} ativo{count !== 1 ? 's' : ''}
                    </span>
                  </button>
                )
              })}
            </div>
          )}
          {activeTypeFilter && (
            <div className="px-4 py-2 border-t border-surface-700 flex items-center justify-between">
              <span className="text-xs text-slate-500">
                Mostrando apenas: <span className="text-slate-300 font-medium">{ASSET_TYPE_LABELS[activeTypeFilter]}</span>
              </span>
              <button
                onClick={() => setActiveTypeFilter(null)}
                className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1"
              >
                <RefreshCw size={11} /> Ver todos
              </button>
            </div>
          )}
        </div>

        {/* Donut */}
        <div className="rounded-xl bg-surface-900 border border-surface-700 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Activity size={15} className="text-brand-500" />
            <span className="text-xs font-semibold text-slate-200">Distribuição</span>
          </div>
          {loadingDist ? (
            <div className="h-52 animate-pulse bg-surface-800 rounded" />
          ) : distribution?.length ? (
            <AssetDonutChart data={distribution} />
          ) : (
            <div className="h-52 flex items-center justify-center text-xs text-slate-500">Sem dados</div>
          )}
        </div>
      </div>

      {/* ── tabela de posições ───────────────────────────────────────────── */}
      <div className="rounded-xl bg-surface-900 border border-surface-700 overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-3 border-b border-surface-700">
          <TrendingUp size={15} className="text-brand-500" />
          <span className="text-xs font-semibold text-slate-200">Posições</span>
          {positions && (
            <span className="ml-1 px-1.5 py-0.5 rounded bg-surface-700 text-slate-400 text-xs tabular-nums">
              {allPositions.length}
            </span>
          )}
          {activeTypeFilter && (
            <span className="ml-auto text-xs text-slate-500">
              Filtrado por: <span className="text-slate-300">{ASSET_TYPE_LABELS[activeTypeFilter]}</span>
            </span>
          )}
        </div>

        {loadingPositions ? (
          <div className="p-4 flex flex-col gap-2">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-10 animate-pulse bg-surface-800 rounded" />
            ))}
          </div>
        ) : filteredPositions.length ? (
          <PositionTable groups={filteredPositions} />
        ) : (
          <EmptyState
            icon={DollarSign}
            title="Nenhum ativo encontrado"
            description="Adicione lançamentos para acompanhar seu patrimônio."
          />
        )}
      </div>
    </div>
  )
}
