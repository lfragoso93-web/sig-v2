import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Wallet,
  Target,
  PieChart,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
  Trophy,
  BarChart3,
  ShoppingCart,
  Info,
  ArrowRight,
  X,
} from 'lucide-react'
import {
  usePortfolioSummary,
  useAssetDistribution,
  usePositions,
  type PositionGroup,
} from '@/hooks/usePortfolio'
import { useClassTargets } from '@/hooks/useClassTargets'
import { useAppStore } from '@/store/appStore'
import { formatBRL, formatPercent, signClass } from '@/utils/format'
import {
  formatReferenceDate,
  getPortfolioReturnPresentation,
  mapPortfolioSummaryMetrics,
} from '@/utils/portfolioSummary'
import KpiCard from '@/components/ui/KpiCard'
import TwrHelpPopover from '@/components/ui/TwrHelpPopover'
import AssetLogo, { resolveClassVisual } from '@/components/ui/AssetLogo'
import SkeletonCard from '@/components/ui/SkeletonCard'
import EmptyState from '@/components/ui/EmptyState'
import AssetDonutChart from '@/components/charts/AssetDonutChart'
import AllocationTargetWidget from '@/components/resume/AllocationTargetWidget'
import PositionTable from '@/components/resume/PositionTable'
import PortfolioEvolutionSection from '@/components/charts/PortfolioEvolutionSection'
import PortfolioReconciliationPanel from '@/components/portfolio/PortfolioReconciliationPanel'
import PendingCorporateFractionsPanel from '@/components/portfolio/PendingCorporateFractionsPanel'
import AssetDetailDrawer from '@/components/portfolio/AssetDetailDrawer'

function safeNum(value: unknown): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function clampPercentage(value: unknown): number {
  return Math.min(Math.max(safeNum(value), 0), 100)
}

function positionValue(position: { current_value?: number | null; invested_value?: number | null }): number {
  return position.current_value == null
    ? safeNum(position.invested_value)
    : safeNum(position.current_value)
}

function positionVariationPct(position: {
  variation_percent?: number | null
  current_value?: number | null
  invested_value?: number | null
}): number {
  if (position.variation_percent != null && Number.isFinite(Number(position.variation_percent))) {
    return Number(position.variation_percent)
  }
  const invested = safeNum(position.invested_value)
  const current = positionValue(position)
  if (invested > 0) {
    return ((current - invested) / invested) * 100
  }
  return 0
}

function PortfolioHighlightsSection({
  portfolioId,
  groups,
  loadingPositions,
  onSelectTicker,
}: {
  portfolioId: number
  groups: PositionGroup[]
  loadingPositions: boolean
  onSelectTicker: (ticker: string) => void
}) {
  const { data: classTargets } = useClassTargets(portfolioId)
  const [showOpportunitiesModal, setShowOpportunitiesModal] = useState(false)

  const positions = useMemo(
    () => (groups ?? []).flatMap(group => group.positions ?? []).filter(p => safeNum(p.quantity) > 0),
    [groups],
  )

  const underAllocatedClasses = useMemo(() => {
    const set = new Set<string>()
    for (const row of classTargets ?? []) {
      if (safeNum(row.target_pct) > safeNum(row.current_pct) + 0.5) {
        set.add(row.asset_type)
      }
    }
    return set
  }, [classTargets])

  const stats = useMemo(() => {
    if (!positions.length) return null

    const enriched = positions.map(p => ({
      ...p,
      varPct: positionVariationPct(p),
      val: positionValue(p),
      belowPm: positionVariationPct(p) < -0.01,
      classUnderTarget: underAllocatedClasses.has(p.asset_type),
    }))

    const sortedByVar = [...enriched].sort((a, b) => b.varPct - a.varPct)
    const best = sortedByVar[0]
    const worst = sortedByVar[sortedByVar.length - 1]

    const profitCount = enriched.filter(p => p.varPct >= 0).length
    const lossCount = enriched.filter(p => p.varPct < 0).length
    const totalCount = enriched.length
    const profitPct = totalCount > 0 ? Math.round((profitCount / totalCount) * 100) : 0
    const lossPct = totalCount > 0 ? Math.max(0, 100 - profitPct) : 0

    // Oportunidades: ativos negociando abaixo do preço médio (desconto) ou de classes abaixo da meta
    const opportunities = enriched
      .filter(p => p.belowPm || p.classUnderTarget)
      .sort((a, b) => a.varPct - b.varPct)

    return {
      best,
      worst,
      profitCount,
      lossCount,
      totalCount,
      profitPct,
      lossPct,
      opportunities,
    }
  }, [positions, underAllocatedClasses])

  if (loadingPositions) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[...Array(3)].map((_, idx) => (
          <div key={idx} className="h-36 skeleton rounded-xl" />
        ))}
      </div>
    )
  }

  if (!stats) return null

  return (
    <>
      <section
        aria-label="Destaques e oportunidades da carteira"
        className="grid grid-cols-1 md:grid-cols-3 gap-4"
      >
        {/* Card 1: Destaques da carteira */}
        <div className="card p-4 sm:p-5 flex flex-col justify-between gap-4">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2.5">
              <span
                aria-hidden="true"
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 'var(--radius-full)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'var(--color-surface-offset)',
                  border: '1px solid var(--color-divider)',
                  color: 'var(--color-text)',
                }}
              >
                <Trophy size={15} strokeWidth={2} />
              </span>
              <span className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                Destaques da carteira
              </span>
            </div>
            <span
              title="Posições abertas com maior e menor rentabilidade acumulada em relação ao preço médio."
              style={{ color: 'var(--color-text-faint)', cursor: 'help' }}
            >
              <Info size={14} />
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4 pt-0.5">
            <div className="flex flex-col items-start gap-1.5 min-w-0">
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                Melhor posição
              </span>
              <button
                type="button"
                onClick={() => onSelectTicker(stats.best.ticker)}
                className="text-sm font-bold truncate hover:underline cursor-pointer"
                style={{ color: 'var(--color-text)', background: 'none', border: 'none', padding: 0 }}
              >
                {stats.best.ticker}
              </button>
              <span
                className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full tabular-nums"
                style={{
                  background: stats.best.varPct >= 0
                    ? 'oklch(from var(--color-success) l c h / 0.16)'
                    : 'oklch(from var(--color-error) l c h / 0.16)',
                  color: stats.best.varPct >= 0 ? 'var(--color-success)' : 'var(--color-error)',
                }}
              >
                {formatPercent(stats.best.varPct)}
                {stats.best.varPct >= 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
              </span>
            </div>

            <div className="flex flex-col items-start gap-1.5 min-w-0">
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                Pior posição
              </span>
              <button
                type="button"
                onClick={() => onSelectTicker(stats.worst.ticker)}
                className="text-sm font-bold truncate hover:underline cursor-pointer"
                style={{ color: 'var(--color-text)', background: 'none', border: 'none', padding: 0 }}
              >
                {stats.worst.ticker}
              </button>
              <span
                className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full tabular-nums"
                style={{
                  background: stats.worst.varPct >= 0
                    ? 'oklch(from var(--color-success) l c h / 0.16)'
                    : 'oklch(from var(--color-error) l c h / 0.16)',
                  color: stats.worst.varPct >= 0 ? 'var(--color-success)' : 'var(--color-error)',
                }}
              >
                {formatPercent(stats.worst.varPct)}
                {stats.worst.varPct >= 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
              </span>
            </div>
          </div>
        </div>

        {/* Card 2: Posições no lucro */}
        <div className="card p-4 sm:p-5 flex flex-col justify-between gap-3.5">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2.5">
              <span
                aria-hidden="true"
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 'var(--radius-full)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'var(--color-surface-offset)',
                  border: '1px solid var(--color-divider)',
                  color: 'var(--color-text)',
                }}
              >
                <BarChart3 size={15} strokeWidth={2} />
              </span>
              <span className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                Posições no lucro
              </span>
            </div>
            <span
              title="Proporção de ativos abertos com cotação atual igual ou superior ao preço médio."
              style={{ color: 'var(--color-text-faint)', cursor: 'help' }}
            >
              <Info size={14} />
            </span>
          </div>

          <div className="flex flex-col gap-2.5">
            <div className="flex items-center gap-2.5">
              <span className="text-xl font-bold tabular-nums" style={{ color: 'var(--color-text)' }}>
                {stats.profitCount} de {stats.totalCount}
              </span>
              <span
                className="text-xs font-semibold px-2.5 py-0.5 rounded-full tabular-nums"
                style={{
                  background: 'oklch(from var(--color-success) l c h / 0.16)',
                  color: 'var(--color-success)',
                }}
              >
                {stats.profitPct}%
              </span>
            </div>

            <div
              className="w-full h-2.5 rounded-full overflow-hidden flex"
              style={{ background: 'var(--color-surface-dynamic)' }}
            >
              {stats.profitCount > 0 && (
                <div
                  className="h-full transition-all"
                  style={{
                    width: `${stats.profitPct}%`,
                    background: 'var(--color-success)',
                  }}
                />
              )}
              {stats.lossCount > 0 && (
                <div
                  className="h-full transition-all"
                  style={{
                    width: `${stats.lossPct}%`,
                    background: 'oklch(from var(--color-error) l c h / 0.75)',
                  }}
                />
              )}
            </div>

            <div className="flex items-center justify-between text-xs font-medium pt-0.5">
              <span className="inline-flex items-center gap-1 tabular-nums" style={{ color: 'var(--color-success)' }}>
                {stats.profitCount} no lucro <span aria-hidden="true">▲</span>
              </span>
              <span className="inline-flex items-center gap-1 tabular-nums" style={{ color: 'var(--color-error)' }}>
                {stats.lossCount} no prejuízo <span aria-hidden="true">▼</span>
              </span>
            </div>
          </div>
        </div>

        {/* Card 3: Oportunidades de compra */}
        <div className="card p-4 sm:p-5 flex flex-col justify-between gap-3.5">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2.5">
              <span
                aria-hidden="true"
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 'var(--radius-full)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'var(--color-surface-offset)',
                  border: '1px solid var(--color-divider)',
                  color: 'var(--color-text)',
                }}
              >
                <ShoppingCart size={15} strokeWidth={2} />
              </span>
              <span className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                Oportunidades de compra
              </span>
            </div>
            <span
              title="Ativos negociados abaixo do seu preço médio atual ou pertencentes a classes abaixo da meta de alocação."
              style={{ color: 'var(--color-text-faint)', cursor: 'help' }}
            >
              <Info size={14} />
            </span>
          </div>

          <div className="flex flex-col gap-3">
            <div className="text-xl font-bold tabular-nums" style={{ color: 'var(--color-text)' }}>
              {stats.opportunities.length} {stats.opportunities.length === 1 ? 'ativo' : 'ativos'}
            </div>

            <button
              type="button"
              onClick={() => setShowOpportunitiesModal(true)}
              disabled={stats.opportunities.length === 0}
              className="w-full py-2 px-4 rounded-full text-xs font-semibold inline-flex items-center justify-center gap-1.5 transition-colors disabled:opacity-40 cursor-pointer"
              style={{
                background: 'var(--color-surface-offset)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text)',
              }}
            >
              <span>Ver ativos</span>
              <ArrowRight size={13} />
            </button>
          </div>
        </div>
      </section>

      {showOpportunitiesModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0, 0, 0, 0.65)', backdropFilter: 'blur(4px)' }}
          onClick={() => setShowOpportunitiesModal(false)}
        >
          <div
            className="card w-full max-w-lg max-h-[80vh] flex flex-col overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            <div className="section-card-header">
              <div className="flex items-center gap-2.5">
                <ShoppingCart size={16} style={{ color: 'var(--color-primary)' }} />
                <div>
                  <span className="section-card-title">Oportunidades de compra</span>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-faint)' }}>
                    Ativos abaixo do preço médio ou em classes abaixo da meta ideal
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowOpportunitiesModal(false)}
                className="p-1.5 rounded-lg"
                style={{ color: 'var(--color-text-muted)' }}
                aria-label="Fechar oportunidades de compra"
              >
                <X size={16} />
              </button>
            </div>

            <div className="section-card-body overflow-y-auto flex flex-col gap-2.5">
              {stats.opportunities.map(item => (
                <div
                  key={item.ticker}
                  className="rounded-xl p-3 flex items-center justify-between gap-3"
                  style={{
                    background: 'var(--color-surface-offset)',
                    border: '1px solid var(--color-divider)',
                  }}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <AssetLogo ticker={item.ticker} assetType={item.asset_type} size={28} logoUrl={item.logo_url} />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <button
                          type="button"
                          onClick={() => {
                            setShowOpportunitiesModal(false)
                            onSelectTicker(item.ticker)
                          }}
                          className="text-sm font-bold hover:underline cursor-pointer"
                          style={{ color: 'var(--color-text)', background: 'none', border: 'none', padding: 0 }}
                        >
                          {item.ticker}
                        </button>
                        {item.belowPm && (
                          <span
                            className="text-[11px] px-2 py-0.5 rounded-full font-medium"
                            style={{
                              background: 'oklch(from var(--color-error) l c h / 0.14)',
                              color: 'var(--color-error)',
                            }}
                          >
                            Abaixo do PM ({formatPercent(item.varPct)})
                          </span>
                        )}
                        {item.classUnderTarget && (
                          <span
                            className="text-[11px] px-2 py-0.5 rounded-full font-medium"
                            style={{
                              background: 'oklch(from var(--color-primary) l c h / 0.14)',
                              color: 'var(--color-primary)',
                            }}
                          >
                            Classe abaixo da meta
                          </span>
                        )}
                      </div>
                      <div className="text-xs mt-0.5 truncate" style={{ color: 'var(--color-text-muted)' }}>
                        PM: {formatBRL(safeNum(item.average_price))} · Atual:{' '}
                        {item.current_price != null ? formatBRL(safeNum(item.current_price)) : '—'}
                      </div>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-xs font-semibold tabular-nums" style={{ color: 'var(--color-text)' }}>
                      {formatBRL(item.val)}
                    </div>
                    <div className="text-[11px] tabular-nums" style={{ color: 'var(--color-text-faint)' }}>
                      {safeNum(item.allocation_pct).toFixed(1)}% da carteira
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  )
}

function ConsolidationSection({
  portfolioId,
  groups,
  loadingPositions,
}: {
  portfolioId: number
  groups: PositionGroup[]
  loadingPositions: boolean
}) {
  const { data: distribution, isLoading: loadingDistribution } = useAssetDistribution(portfolioId)

  const counts = useMemo(() => {
    const result: Record<string, number> = {}
    for (const group of groups ?? []) {
      const assetType = group.positions?.[0]?.asset_type
      if (assetType) result[assetType] = group.count
    }
    return result
  }, [groups])

  return (
    <section className="card overflow-hidden flex flex-col h-full" aria-label="Consolidação do patrimônio">
      <div className="section-card-header">
        <div className="flex items-center gap-2.5">
          <span
            aria-hidden="true"
            style={{
              width: 28,
              height: 28,
              borderRadius: 'var(--radius-md)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'oklch(from var(--color-primary) l c h / 0.1)',
              color: 'var(--color-primary)',
            }}
          >
            <PieChart size={14} strokeWidth={2} />
          </span>
          <div>
            <span className="section-card-title">Consolidação do patrimônio</span>
            <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-faint)' }}>
              Distribuição por classe calculada pelo valuation intradiário canônico.
            </p>
          </div>
        </div>
      </div>

      <div className="section-card-body flex-1">
        {loadingDistribution || loadingPositions ? (
          <div className="h-56 skeleton rounded-xl" />
        ) : !distribution?.length ? (
          <div
            className="h-56 flex items-center justify-center text-sm"
            style={{ color: 'var(--color-text-muted)' }}
          >
            Sem posições para consolidar.
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-[minmax(260px,320px)_1fr] gap-6 items-center">
            <div className="flex justify-center w-full">
              <AssetDonutChart data={distribution} />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {distribution.map(item => {
                const { Icon: ClassIcon, color: classColor, bg: classBg } = resolveClassVisual(item.asset_type)
                const safePct = clampPercentage(item.percentage)
                const count = counts[item.asset_type] ?? 0
                return (
                  <div
                    key={item.asset_type}
                    className="rounded-xl p-4 flex flex-col justify-between gap-3"
                    style={{
                      background: 'var(--color-surface-offset)',
                      border: '1px solid var(--color-divider)',
                    }}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          aria-hidden="true"
                          style={{
                            width: 24,
                            height: 24,
                            borderRadius: 'var(--radius-sm)',
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0,
                            background: classBg,
                            color: item.color ?? classColor,
                          }}
                        >
                          <ClassIcon size={13} strokeWidth={2} />
                        </span>
                        <span
                          className="text-xs font-semibold truncate"
                          style={{ color: 'var(--color-text)' }}
                          title={item.label}
                        >
                          {item.label}
                        </span>
                      </div>
                      <span
                        className="text-[11px] px-2 py-0.5 rounded-full shrink-0"
                        style={{
                          color: 'var(--color-text-muted)',
                          background: 'var(--color-surface)',
                          border: '1px solid oklch(from var(--color-text) l c h / 0.06)',
                        }}
                      >
                        {count} ativo{count === 1 ? '' : 's'}
                      </span>
                    </div>

                    <div>
                      <div className="flex items-end justify-between gap-3 mb-2">
                        <span className="text-sm font-semibold tabular-nums" style={{ color: 'var(--color-text)' }}>
                          {formatBRL(safeNum(item.value))}
                        </span>
                        <span
                          className="text-xs font-semibold tabular-nums"
                          style={{ color: item.color ?? 'var(--color-primary)' }}
                        >
                          {safePct.toFixed(1)}%
                        </span>
                      </div>
                      <div
                        className="w-full h-1.5 rounded-full overflow-hidden"
                        style={{ background: 'var(--color-surface-dynamic)' }}
                      >
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${safePct}%`,
                            background: item.color ?? 'var(--color-primary)',
                          }}
                        />
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

function AllocationTargetsCard({ portfolioId }: { portfolioId: number }) {
  const { data: classTargets, isLoading: loadingTargets } = useClassTargets(portfolioId)

  return (
    <section className="card overflow-hidden flex flex-col h-full" aria-label="Alocação ideal versus atual">
      <div className="section-card-header">
        <div className="flex items-center gap-2.5">
          <span
            aria-hidden="true"
            style={{
              width: 28,
              height: 28,
              borderRadius: 'var(--radius-md)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'oklch(from var(--color-primary) l c h / 0.1)',
              color: 'var(--color-primary)',
            }}
          >
            <Target size={14} strokeWidth={2} />
          </span>
          <div>
            <span className="section-card-title">Distribuição ideal versus atual</span>
            <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-faint)' }}>
              Comparação entre o peso atual e as metas por classe.
            </p>
          </div>
        </div>
        <Link
          to="/carteira/metas"
          className="inline-flex items-center gap-1 text-xs font-semibold hover:underline shrink-0"
          style={{ color: 'var(--color-primary)' }}
        >
          <span>Metas</span>
          <ArrowUpRight size={13} aria-hidden="true" />
        </Link>
      </div>

      <div className="section-card-body flex-1 flex flex-col justify-center">
        {loadingTargets ? (
          <div className="h-36 skeleton rounded-xl" />
        ) : classTargets?.length ? (
          <AllocationTargetWidget rows={classTargets} noTopMargin />
        ) : (
          <div
            className="rounded-xl p-5 text-center"
            style={{
              background: 'var(--color-surface-offset)',
              border: '1px dashed oklch(from var(--color-text) l c h / 0.12)',
            }}
          >
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Nenhuma meta de alocação por classe configurada para esta carteira.
            </p>
            <Link
              to="/carteira/metas"
              className="inline-block mt-2 text-xs font-semibold hover:underline"
              style={{ color: 'var(--color-primary)' }}
            >
              Configurar metas de alocação
            </Link>
          </div>
        )}
      </div>
    </section>
  )
}

function ConcentrationSection({
  groups,
  onSelectTicker,
}: {
  groups: PositionGroup[]
  onSelectTicker: (ticker: string) => void
}) {
  const positions = useMemo(() => groups.flatMap(group => group.positions ?? []), [groups])
  const ranked = useMemo(() => {
    const total = positions.reduce((sum, position) => sum + positionValue(position), 0)
    return positions
      .map(position => ({
        ticker: position.ticker,
        assetType: position.asset_type,
        logoUrl: position.logo_url,
        value: positionValue(position),
        percentage: total > 0 ? (positionValue(position) / total) * 100 : 0,
      }))
      .filter(item => item.value > 0)
      .sort((a, b) => b.value - a.value)
  }, [positions])

  const hhi = ranked.reduce((sum, item) => sum + item.percentage ** 2, 0)
  const label = hhi < 1500 ? 'Bem diversificado' : hhi < 2500 ? 'Concentração moderada' : 'Alta concentração'
  const color = hhi < 1500 ? 'var(--color-success)' : hhi < 2500 ? 'var(--color-gold)' : 'var(--color-error)'

  if (!ranked.length) return null

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <section className="card overflow-hidden flex flex-col" aria-label="Índice de concentração">
        <div className="section-card-header">
          <div className="flex items-center gap-2">
            <PieChart size={14} style={{ color: 'var(--color-primary)' }} />
            <span className="section-card-title">Concentração</span>
          </div>
        </div>
        <div className="section-card-body flex flex-col justify-between flex-1 gap-3">
          <div>
            <div className="text-3xl font-bold tabular-nums" style={{ color }}>
              {Math.round(hhi).toLocaleString('pt-BR')}
            </div>
            <div className="text-sm font-semibold mt-1" style={{ color }}>
              {label}
            </div>
          </div>
          <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text-faint)' }}>
            Índice HHI calculado sobre o valuation intradiário das posições abertas.
          </p>
        </div>
      </section>

      <section className="card overflow-hidden lg:col-span-2" aria-label="Maiores posições da carteira">
        <div className="section-card-header">
          <span className="section-card-title">Top 5 posições</span>
          <span className="text-xs" style={{ color: 'var(--color-text-faint)' }}>
            Participação no patrimônio atual
          </span>
        </div>
        <div className="section-card-body flex flex-col gap-3.5">
          {ranked.slice(0, 5).map((item, index) => {
            const safePct = clampPercentage(item.percentage)
            return (
              <div key={item.ticker} className="flex items-center gap-3 min-w-0">
                <span className="text-xs font-medium w-6 shrink-0" style={{ color: 'var(--color-text-faint)' }}>
                  #{index + 1}
                </span>
                <AssetLogo ticker={item.ticker} assetType={item.assetType} size={26} logoUrl={item.logoUrl} />
                <button
                  type="button"
                  onClick={() => onSelectTicker(item.ticker)}
                  className="text-sm font-semibold w-24 truncate text-left hover:underline cursor-pointer shrink-0"
                  style={{ color: 'var(--color-text)', background: 'none', border: 'none', padding: 0 }}
                >
                  {item.ticker}
                </button>
                <div
                  className="flex-1 h-2 rounded-full overflow-hidden min-w-[60px]"
                  style={{ background: 'var(--color-surface-dynamic)' }}
                >
                  <div
                    className="h-full rounded-full transition-all"
                    style={{ width: `${safePct}%`, background: 'var(--color-primary)' }}
                  />
                </div>
                <span className="text-xs w-14 text-right tabular-nums font-medium shrink-0" style={{ color: 'var(--color-text-muted)' }}>
                  {safePct.toFixed(1)}%
                </span>
                <span className="text-xs w-28 text-right tabular-nums font-semibold hidden sm:inline-block shrink-0">
                  {formatBRL(item.value)}
                </span>
              </div>
            )
          })}
        </div>
      </section>
    </div>
  )
}

export default function PatrimonioPage() {
  const portfolioId = useAppStore(state => state.selectedPortfolioId)
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)
  const { data: summary, isLoading: loadingSummary, error: summaryError } = usePortfolioSummary(portfolioId ?? 0)
  const metrics = summary ? mapPortfolioSummaryMetrics(summary) : null
  const returnPresentation = getPortfolioReturnPresentation(metrics)
  const summaryContractError = summaryError instanceof Error
    && summaryError.message.startsWith('Contrato summary.v2 inválido:')
  const { data: groups = [], isLoading: loadingPositions } = usePositions(portfolioId ?? 0)

  if (!portfolioId) {
    return (
      <div className="p-6">
        <EmptyState
          icon={Wallet}
          title="Nenhuma carteira selecionada"
          description="Selecione uma carteira no menu superior para visualizar o patrimônio."
        />
      </div>
    )
  }

  const valuationReference = formatReferenceDate(metrics?.valuationUpdatedAt)
  const performanceReference = formatReferenceDate(metrics?.performanceAsOf)
  const proventosReference = formatReferenceDate(metrics?.proventosAsOf)
  const totalPositionsCount = groups.reduce((acc, group) => acc + (group.count ?? 0), 0)

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Patrimônio</h1>
          <p className="page-subtitle">Valuation intradiário, consolidação por classe, metas e posições</p>
        </div>
      </div>

      {/* Bloco 1: KPIs de Resumo Patrimonial */}
      <div className="kpi-grid">
        {loadingSummary ? (
          [...Array(4)].map((_, index) => <SkeletonCard key={index} />)
        ) : summaryContractError ? (
          <div
            className="col-span-4 rounded-xl px-4 py-5 text-center"
            style={{
              color: 'var(--color-error)',
              border: '1px solid oklch(from var(--color-error) l c h / 0.25)',
              background: 'oklch(from var(--color-error) l c h / 0.08)',
            }}
          >
            <p className="text-sm font-semibold">Contrato financeiro inválido. Os KPIs foram ocultados.</p>
            <p className="text-xs mt-1">{summaryError.message}</p>
          </div>
        ) : summary && metrics ? (
          <>
            <KpiCard
              label="Patrimônio atual"
              value={formatBRL(metrics.patrimonio)}
              subValue={formatBRL(metrics.aportado)}
              subLabel="Custo das posições abertas"
            />
            <KpiCard
              label="Resultado patrimonial"
              value={formatBRL(metrics.ganhoNaoRealizado)}
              valueColor={signClass(metrics.ganhoNaoRealizado)}
              change={metrics.variacaoPct}
              subLabel="Não realizado sobre posições abertas"
            />
            <KpiCard
              label="Resultado total"
              value={formatBRL(metrics.lucroTotal)}
              valueColor={signClass(metrics.lucroTotal)}
              subValue={formatBRL(metrics.ganhoRealizado)}
              subLabel="Realizado; total inclui proventos"
            />
            <KpiCard
              label={returnPresentation.label}
              value={`${metrics.rentabilidadePct >= 0 ? '+' : ''}${formatPercent(metrics.rentabilidadePct)}`}
              valueColor={signClass(metrics.rentabilidadePct)}
              subValue={formatBRL(metrics.proventosTotal)}
              subLabel="Proventos líquidos recebidos"
              bottomLine={
                returnPresentation.isEstimated ? (
                  <span className="text-xs font-semibold" style={{ color: 'var(--color-warning)' }}>
                    Estimativa do valuation atual; TWR indisponível sem snapshot
                  </span>
                ) : undefined
              }
            />
          </>
        ) : (
          <div className="col-span-4 py-8 text-center text-xs" style={{ color: 'var(--color-text-muted)' }}>
            Nenhum dado disponível.
          </div>
        )}
      </div>

      {summary && metrics && (
        <div
          className="card px-4 py-3 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs"
          style={{ color: 'var(--color-text-muted)' }}
        >
          <span>Patrimônio e posições: {valuationReference ?? 'sem horário de cotação'}</span>
          <span className="inline-flex items-center gap-1">
            <span>
              TWR até: {performanceReference ?? 'sem snapshot fechado'}
              {metrics.returnIsEstimated ? ' (estimado)' : ''}
            </span>
            <TwrHelpPopover size={12} />
          </span>
          <span>Proventos até: {proventosReference ?? '—'}</span>
          <span>Cobertura de preços: {safeNum(summary.price_coverage_pct).toFixed(1)}%</span>
        </div>
      )}

      {/* Bloco 1.5: Destaques da Carteira, Posições no Lucro e Oportunidades de Compra */}
      <PortfolioHighlightsSection
        portfolioId={portfolioId}
        groups={groups}
        loadingPositions={loadingPositions}
        onSelectTicker={setSelectedTicker}
      />

      <PortfolioReconciliationPanel portfolioId={portfolioId} />
      <PendingCorporateFractionsPanel portfolioId={portfolioId} />

      {/* Bloco 2: Evolução do Patrimônio */}
      <PortfolioEvolutionSection portfolioId={portfolioId} />

      {/* Bloco 3: Consolidação por Classe & Alocação Ideal vs. Atual (separados em cards próprios) */}
      <div className="grid grid-cols-1 xl:grid-cols-[1.6fr_1fr] gap-5 items-stretch">
        <ConsolidationSection
          portfolioId={portfolioId}
          groups={groups}
          loadingPositions={loadingPositions}
        />
        <AllocationTargetsCard portfolioId={portfolioId} />
      </div>

      {/* Bloco 4: Concentração & Top 5 Posições */}
      <ConcentrationSection groups={groups} onSelectTicker={setSelectedTicker} />

      {/* Bloco 5: Posições da Carteira (separadas visualmente) */}
      <section className="flex flex-col gap-3.5" aria-label="Posições da carteira">
        <div className="flex items-center gap-3">
          <Layers size={15} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
          <span
            style={{
              fontSize: 'var(--text-sm)',
              fontWeight: 700,
              letterSpacing: '-0.01em',
              color: 'var(--color-text)',
            }}
          >
            Posições por Classe
          </span>
          {totalPositionsCount > 0 && (
            <span
              style={{
                fontSize: 'var(--text-xs)',
                fontWeight: 500,
                color: 'var(--color-text-muted)',
                background: 'var(--color-surface-offset)',
                border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
                borderRadius: 'var(--radius-full)',
                padding: '1px 8px',
              }}
            >
              {totalPositionsCount} ativo{totalPositionsCount === 1 ? '' : 's'}
            </span>
          )}
          <div style={{ flex: 1, height: 1, background: 'oklch(from var(--color-text) l c h / 0.08)' }} />
        </div>

        {loadingPositions ? (
          <div className="flex flex-col gap-3">
            {[...Array(2)].map((_, idx) => (
              <div key={idx} className="h-28 skeleton rounded-xl" />
            ))}
          </div>
        ) : groups.length > 0 ? (
          <PositionTable groups={groups} portfolioId={portfolioId} />
        ) : (
          <div className="card p-6 text-center text-xs" style={{ color: 'var(--color-text-muted)' }}>
            Nenhuma posição aberta encontrada nesta carteira.
          </div>
        )}
      </section>

      {selectedTicker && (
        <AssetDetailDrawer
          ticker={selectedTicker}
          portfolioId={portfolioId}
          onClose={() => setSelectedTicker(null)}
        />
      )}
    </div>
  )
}
