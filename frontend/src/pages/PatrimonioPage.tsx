import { useMemo, useState } from 'react'
import {
  BarChart2, RefreshCw, Wallet, Target, TrendingUp, TrendingDown,
  LineChart, AlertTriangle, PieChart, ArrowUp, ArrowDown, Minus,
} from 'lucide-react'
import {
  usePortfolioSummary,
  useAssetDistribution,
  usePositions,
  type PositionGroup,
} from '@/hooks/usePortfolio'
import {
  useDailyEvolution,
  useMonthlyEvolution,
  useEvolutionBackfill,
  type PeriodOption,
} from '@/hooks/useEvolution'
import { useClassTargets } from '@/hooks/useClassTargets'
import { useAppStore } from '@/store/appStore'
import { formatBRL, formatPercent, signClass } from '@/utils/format'
import KpiCard from '@/components/ui/KpiCard'
import SkeletonCard from '@/components/ui/SkeletonCard'
import EmptyState from '@/components/ui/EmptyState'
import AssetDonutChart from '@/components/charts/AssetDonutChart'
import PositionTable from '@/components/resume/PositionTable'
import AllocationTargetWidget from '@/components/resume/AllocationTargetWidget'
import EvolutionLineChart from '@/components/charts/EvolutionLineChart'
import EvolutionBarChart from '@/components/charts/EvolutionBarChart'
import ConcentrationTreemap from '@/components/charts/ConcentrationTreemap'
import clsx from 'clsx'

// ── Constantes ────────────────────────────────────────────────────────────────────────────────────
const ASSET_TYPE_LABELS: Record<string, string> = {
  ACAO: 'Ações', ACAO_NACIONAL: 'Ações', FII: 'FIIs',
  ETF_NACIONAL: 'ETFs BR', STOCK: 'Stocks', ETF_INTERNACIONAL: 'ETFs INT',
  TESOURO_DIRETO: 'Tesouro Direto', RENDA_FIXA: 'Renda Fixa', CRIPTO: 'Cripto',
  BDR: 'BDRs',
}

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
  BDR:               { bg: 'var(--color-purple-highlight)', text: 'var(--color-purple)', border: 'var(--color-purple-highlight)' },
}
const FALLBACK_COLOR = { bg: 'var(--color-surface-dynamic)', text: 'var(--color-text-muted)', border: 'var(--color-border)' }

// cores sólidas para treemap por tipo de ativo
const TREEMAP_COLOR_MAP: Record<string, string> = {
  ACAO:              'var(--color-blue)',
  ACAO_NACIONAL:     'var(--color-blue)',
  FII:               'var(--color-purple)',
  ETF_NACIONAL:      'var(--color-primary)',
  STOCK:             '#3b82f6',
  ETF_INTERNACIONAL: '#6366f1',
  TESOURO_DIRETO:    'var(--color-gold)',
  RENDA_FIXA:        'var(--color-orange)',
  CRIPTO:            'var(--color-error)',
  BDR:               '#a855f7',
}
const TREEMAP_FALLBACK = 'var(--color-text-muted)'

const PERIODS: { label: string; value: PeriodOption }[] = [
  { label: '6m',   value: '6m'  },
  { label: '12m',  value: '12m' },
  { label: '24m',  value: '24m' },
  { label: 'Tudo', value: 'all' },
]

type Tab = 'visao-geral' | 'historico' | 'analise'
type ViewMode = 'diario' | 'mensal'
type TreemapView = 'ativo' | 'classe'

// ── Tab bar ────────────────────────────────────────────────────────────────────────────────────
function TabBar({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
    { id: 'visao-geral', label: 'Visão Geral', icon: BarChart2 },
    { id: 'historico',   label: 'Histórico',    icon: LineChart  },
    { id: 'analise',     label: 'Análise',       icon: PieChart  },
  ]
  return (
    <div
      className="flex gap-1 p-1 rounded-xl"
      style={{ background: 'var(--color-surface-dynamic)', width: 'fit-content' }}
    >
      {tabs.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          onClick={() => onChange(id)}
          className="flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-all"
          style={{
            background: active === id ? 'var(--color-surface)' : 'transparent',
            color:      active === id ? 'var(--color-text)'    : 'var(--color-text-muted)',
            boxShadow:  active === id ? 'var(--shadow-sm)'     : 'none',
          }}
        >
          <Icon size={14} strokeWidth={1.75} />
          {label}
        </button>
      ))}
    </div>
  )
}

// ── Toggle group ──────────────────────────────────────────────────────────────────────────────
function ToggleGroup<T extends string>({
  options, value, onChange,
}: {
  options: { label: string; value: T }[]
  value: T
  onChange: (v: T) => void
}) {
  return (
    <div
      className="flex"
      style={{ border: '1px solid var(--color-border)', background: 'var(--color-surface)', borderRadius: 'var(--radius-lg)' }}
    >
      {options.map((opt, idx) => {
        const isActive = value === opt.value
        const isFirst  = idx === 0
        const isLast   = idx === options.length - 1
        return (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className="px-3 py-1.5 text-xs font-medium transition-colors"
            style={{
              background:   isActive ? 'var(--color-primary)' : 'transparent',
              color:        isActive ? '#fff' : 'var(--color-text-muted)',
              borderRadius: isFirst && isLast
                ? 'calc(var(--radius-lg) - 1px)'
                : isFirst
                  ? 'calc(var(--radius-lg) - 1px) 0 0 calc(var(--radius-lg) - 1px)'
                  : isLast
                    ? '0 calc(var(--radius-lg) - 1px) calc(var(--radius-lg) - 1px) 0'
                    : '0',
              minWidth: '3.5rem',
            }}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}

// ── Aba: Visao Geral ────────────────────────────────────────────────────────────────────────────────────────
function TabVisaoGeral({ portfolioId }: { portfolioId: number }) {
  const [activeTypeFilter, setActiveTypeFilter] = useState<string | null>(null)

  const { data: summary,      isLoading: loadingSummary  } = usePortfolioSummary(portfolioId)
  const { data: distribution, isLoading: loadingDist     } = useAssetDistribution(portfolioId)
  const { data: positions,    isLoading: loadingPositions } = usePositions(portfolioId)
  const { data: classTargets, isLoading: loadingTargets  } = useClassTargets(portfolioId)

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
      .map((g: PositionGroup) => ({ ...g, positions: g.positions.filter((p: any) => p.asset_type === activeTypeFilter) }))
      .filter((g: PositionGroup) => g.positions.length > 0)
  }, [positions, activeTypeFilter])

  return (
    <>
      {/* KPIs */}
      <div className="kpi-grid">
        {loadingSummary ? (
          [...Array(4)].map((_, i) => <SkeletonCard key={i} />)
        ) : summary ? (
          <>
            <KpiCard
              label="Patrimônio Total"
              value={formatBRL(summary.total_patrimonio ?? 0)}
              subValue={formatBRL(summary.total_investido ?? 0)}
              subLabel="Valor investido"
              change={summary.variacao_percentual}
            />
            <KpiCard
              label="Resultado"
              value={formatBRL(summary.lucro_total ?? 0)}
              valueColor={signClass(summary.lucro_total ?? 0)}
              subLabel="Ganho de capital + proventos"
            />
            <KpiCard
              label="Proventos (12m)"
              value={formatBRL(summary.dividendos_recebidos_12m ?? 0)}
              subValue={formatBRL(summary.total_proventos ?? 0)}
              subLabel="Total recebido"
            />
            <KpiCard
              label="Variação"
              value={formatBRL(summary.variacao_valor ?? 0)}
              valueColor={signClass(summary.variacao_valor ?? 0)}
              change={summary.variacao_percentual}
              bottomLine={
                <span className={clsx('text-xs font-semibold tabular-nums', signClass(summary.rentabilidade_total ?? 0))}>
                  {(summary.rentabilidade_total ?? 0) >= 0 ? '+' : ''}{formatPercent(summary.rentabilidade_total ?? 0)} rentab.
                </span>
              }
            />
          </>
        ) : (
          <div className="col-span-4 py-8 text-center text-xs" style={{ color: 'var(--color-text-muted)' }}>
            Nenhum dado disponível. Adicione lançamentos para começar.
          </div>
        )}
      </div>

      {/* Breakdown por classe + donut + alvo */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 card overflow-hidden">
          <div className="section-card-header">
            <BarChart2 size={14} style={{ color: 'var(--color-primary)' }} />
            <span className="section-card-title">Alocação por Classe</span>
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
            <div>
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
                      background:   isActive ? 'var(--color-surface-offset)' : 'transparent',
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

        {/* Donut + Alvo da Carteira */}
        <div className="card overflow-hidden">
          <div className="section-card-header">
            <span className="section-card-title">Distribuição</span>
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

          <div style={{ padding: '0 1rem 1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: '0.5rem', paddingTop: '0.75rem', borderTop: '1px solid var(--color-divider)' }}>
              <Target size={12} style={{ color: 'var(--color-primary)' }} />
              <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-muted)' }}>
                Distribuição Ideal vs. Atual
              </span>
            </div>
            {loadingTargets ? (
              <div className="animate-pulse rounded-md" style={{ height: 80, background: 'var(--color-surface-offset)' }} />
            ) : classTargets && classTargets.length > 0 ? (
              <AllocationTargetWidget rows={classTargets} noTopMargin />
            ) : (
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)' }}>
                Configure metas em{' '}
                <a href="/carteira/metas" style={{ color: 'var(--color-primary)', textDecoration: 'underline' }}>
                  Configurações → Metas
                </a>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Tabela de posições */}
      <div className="card overflow-hidden">
        <div className="section-card-header" style={{ justifyContent: 'space-between' }}>
          <div className="flex items-center gap-2">
            <span className="section-card-title">Posições</span>
            <span
              className="px-1.5 py-0.5 rounded text-xs tabular-nums"
              style={{ background: 'var(--color-surface-dynamic)', color: 'var(--color-text-muted)' }}
            >
              {filteredPositions.reduce((s: number, g: PositionGroup) => s + g.count, 0)}
            </span>
          </div>
          {activeTypeFilter && (
            <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Filtrado por: <span className="font-medium" style={{ color: 'var(--color-text)' }}>{ASSET_TYPE_LABELS[activeTypeFilter] ?? activeTypeFilter}</span>
            </span>
          )}
        </div>
        {loadingPositions ? (
          <div className="p-4 flex flex-col gap-2">
            {[...Array(4)].map((_, i) => <div key={i} className="h-12 rounded skeleton" />)}
          </div>
        ) : (
          <PositionTable groups={filteredPositions} portfolioId={portfolioId} />
        )}
      </div>
    </>
  )
}

// ── Aba: Historico ────────────────────────────────────────────────────────────────────────────────────────
function TabHistorico({ portfolioId }: { portfolioId: number }) {
  const [period,       setPeriod]       = useState<PeriodOption>('12m')
  const [view,         setView]         = useState<ViewMode>('diario')
  const [backfillDone, setBackfillDone] = useState(false)

  const { data: daily,   isLoading: loadingDaily   } = useDailyEvolution(portfolioId, period)
  const { data: monthly, isLoading: loadingMonthly } = useMonthlyEvolution(portfolioId, period)
  const backfill = useEvolutionBackfill(portfolioId)

  const last  = daily && daily.length > 0 ? daily[daily.length - 1] : null
  const first = daily && daily.length > 0 ? daily[0] : null
  const variacao    = last && first ? last.market_value - first.market_value : null
  const variacaoPct = last && first && first.market_value > 0
    ? ((last.market_value - first.market_value) / first.market_value) * 100
    : null

  const handleBackfill = async () => {
    await backfill.mutateAsync()
    setBackfillDone(true)
    setTimeout(() => setBackfillDone(false), 3000)
  }

  const noData = !loadingDaily && (!daily || daily.length === 0)

  const viewOptions: { label: string; value: ViewMode }[] = [
    { label: 'Diário', value: 'diario' },
    { label: 'Mensal', value: 'mensal' },
  ]

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <ToggleGroup<ViewMode> options={viewOptions} value={view} onChange={setView} />
          <ToggleGroup<PeriodOption> options={PERIODS} value={period} onChange={setPeriod} />
        </div>
        <button
          onClick={handleBackfill}
          disabled={backfill.isPending}
          className="btn btn-ghost flex items-center gap-2 text-sm"
          title="Recalcular snapshots históricos"
        >
          <RefreshCw size={14} className={clsx(backfill.isPending && 'animate-spin')} />
          {backfillDone ? 'Atualizado!' : 'Atualizar histórico'}
        </button>
      </div>

      <div className="kpi-grid">
        {loadingDaily ? (
          [...Array(4)].map((_, i) => <SkeletonCard key={i} />)
        ) : last ? (
          <>
            <KpiCard label="Valor atual (mercado)" value={formatBRL(last.market_value)} subValue={formatBRL(last.invested_total)} subLabel="Total investido" />
            <KpiCard label="Resultado total" value={formatBRL(last.total_pnl)} valueColor={signClass(last.total_pnl)} subLabel={`Realizado: ${formatBRL(last.realized_pnl)}`} />
            <KpiCard label={`Variação no período (${period})`} value={variacao !== null ? formatBRL(variacao) : '—'} valueColor={variacao !== null ? signClass(variacao) : undefined} change={variacaoPct ?? undefined} />
            <KpiCard label="Rentabilidade total" value={formatPercent(last.return_pct)} valueColor={signClass(last.return_pct)} subLabel="Sobre o capital investido" />
          </>
        ) : (
          <div className="col-span-4 py-8 text-center text-xs" style={{ color: 'var(--color-text-muted)' }}>
            Nenhum snapshot encontrado. Clique em “Atualizar histórico” para gerar os dados.
          </div>
        )}
      </div>

      <div className="card">
        <div className="section-card-header">
          {view === 'diario' ? <TrendingUp size={14} style={{ color: 'var(--color-primary)' }} /> : <BarChart2 size={14} style={{ color: 'var(--color-primary)' }} />}
          <span className="section-card-title">{view === 'diario' ? 'Evolução Diária' : 'Evolução Mensal'}</span>
        </div>
        <div className="p-4">
          {noData ? (
            <div className="flex flex-col items-center gap-3 py-10" style={{ color: 'var(--color-text-muted)' }}>
              <AlertTriangle size={24} style={{ color: 'var(--color-warning, #f59e0b)' }} />
              <p className="text-sm text-center">Nenhum dado histórico encontrado.<br />Clique em <strong>Atualizar histórico</strong> acima para gerar os snapshots.</p>
            </div>
          ) : view === 'diario' ? (
            loadingDaily ? <div className="h-64 skeleton rounded" /> : <EvolutionLineChart data={daily ?? []} />
          ) : (
            loadingMonthly ? <div className="h-64 skeleton rounded" /> : <EvolutionBarChart data={monthly ?? []} />
          )}
        </div>
      </div>

      {!loadingMonthly && monthly && monthly.length > 0 && (
        <div className="card overflow-hidden">
          <div className="section-card-header"><span className="section-card-title">Resumo Mensal</span></div>
          <div className="overflow-x-auto">
            <table className="table-dense w-full">
              <thead>
                <tr>
                  <th>Mês</th>
                  <th className="text-right">Valor mercado</th>
                  <th className="text-right">Investido</th>
                  <th className="text-right">P&amp;L não realiz.</th>
                  <th className="text-right">Rentab.</th>
                </tr>
              </thead>
              <tbody>
                {[...monthly].reverse().map((row, i) => {
                  const isPositive = row.return_pct >= 0
                  const isCurrentMonth = i === 0
                  return (
                    <tr key={row.period} style={{ background: isCurrentMonth ? 'oklch(from var(--color-primary) l c h / 0.05)' : 'transparent' }}>
                      <td>
                        <span style={{ color: 'var(--color-text)' }}>{row.period}</span>
                        {isCurrentMonth && <span className="ml-2 badge badge-primary" style={{ fontSize: '0.625rem', padding: '0.1em 0.45em' }}>atual</span>}
                      </td>
                      <td className="text-right tabular-nums" style={{ color: 'var(--color-text)' }}>{formatBRL(row.value)}</td>
                      <td className="text-right tabular-nums" style={{ color: 'var(--color-text-muted)' }}>{formatBRL(row.invested)}</td>
                      <td className={clsx('text-right tabular-nums', signClass(row.unrealized_pnl))}>{row.unrealized_pnl >= 0 ? '+' : ''}{formatBRL(row.unrealized_pnl)}</td>
                      <td className={clsx('text-right tabular-nums font-medium', signClass(row.return_pct))}>
                        <span className="inline-flex items-center justify-end gap-1">
                          {isPositive ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                          {row.return_pct >= 0 ? '+' : ''}{formatPercent(row.return_pct)}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  )
}

// ── Aba: Analise (Sprint 6B) ─────────────────────────────────────────────────────────────────────────────────
function TabAnalise({ portfolioId }: { portfolioId: number }) {
  const [treemapView, setTreemapView] = useState<TreemapView>('ativo')

  const { data: positions, isLoading: loadingPositions } = usePositions(portfolioId)
  const { data: classTargets }                           = useClassTargets(portfolioId)

  // Flatten positions
  const allPositions = useMemo(() => {
    if (!positions) return []
    return positions.flatMap((g: PositionGroup) => g.positions ?? [])
  }, [positions])

  // Treemap: por ativo individual
  const treemapByAsset = useMemo(() => {
    const total = allPositions.reduce((s: number, p: any) => s + (p.current_value ?? 0), 0)
    if (total === 0) return []
    return allPositions
      .filter((p: any) => (p.current_value ?? 0) > 0)
      .map((p: any) => ({
        label: p.ticker ?? p.asset_code ?? '?',
        value: p.current_value ?? 0,
        color: TREEMAP_COLOR_MAP[p.asset_type] ?? TREEMAP_FALLBACK,
      }))
      .sort((a: any, b: any) => b.value - a.value)
  }, [allPositions])

  // Treemap: por classe
  const treemapByClass = useMemo(() => {
    const map: Record<string, number> = {}
    for (const p of allPositions) {
      const t = p.asset_type ?? 'OUTROS'
      map[t] = (map[t] ?? 0) + (p.current_value ?? 0)
    }
    return Object.entries(map)
      .filter(([, v]) => v > 0)
      .map(([type, value]) => ({
        label: ASSET_TYPE_LABELS[type] ?? type,
        value,
        color: TREEMAP_COLOR_MAP[type] ?? TREEMAP_FALLBACK,
      }))
      .sort((a, b) => b.value - a.value)
  }, [allPositions])

  // HHI (0-10000): soma dos quadrados das porcentagens
  const { hhi, hhiNorm, hhiLevel, hhiLabel } = useMemo(() => {
    const items = treemapView === 'ativo' ? treemapByAsset : treemapByClass
    const total = items.reduce((s, i) => s + i.value, 0)
    if (total === 0) return { hhi: 0, hhiNorm: 0, hhiLevel: 'neutro', hhiLabel: '—' }
    const hhi = items.reduce((s, i) => {
      const pct = (i.value / total) * 100
      return s + pct * pct
    }, 0)
    const hhiNorm = Math.min(hhi / 10000, 1)
    let hhiLevel: 'baixo' | 'medio' | 'alto' | 'neutro' = 'neutro'
    let hhiLabel = '—'
    if (hhi < 1500)       { hhiLevel = 'baixo'; hhiLabel = 'Bem diversificado' }
    else if (hhi < 2500)  { hhiLevel = 'medio'; hhiLabel = 'Concentração moderada' }
    else                  { hhiLevel = 'alto';  hhiLabel = 'Alta concentração' }
    return { hhi, hhiNorm, hhiLevel, hhiLabel }
  }, [treemapByAsset, treemapByClass, treemapView])

  // Desvio por classe: atual vs alvo
  const desvioRows = useMemo(() => {
    if (!classTargets || classTargets.length === 0) return []
    return classTargets
      .map((row: any) => ({
        label:   ASSET_TYPE_LABELS[row.asset_class] ?? row.asset_class,
        type:    row.asset_class as string,
        target:  row.target_pct as number,
        current: row.current_pct as number,
        delta:   (row.current_pct ?? 0) - (row.target_pct ?? 0),
      }))
      .sort((a: any, b: any) => Math.abs(b.delta) - Math.abs(a.delta))
  }, [classTargets])

  const hhiColor = hhiLevel === 'baixo'
    ? 'var(--color-success)'
    : hhiLevel === 'medio'
      ? 'var(--color-gold)'
      : hhiLevel === 'alto'
        ? 'var(--color-error)'
        : 'var(--color-text-muted)'

  const treemapViewOptions: { label: string; value: TreemapView }[] = [
    { label: 'Por ativo',  value: 'ativo'  },
    { label: 'Por classe', value: 'classe' },
  ]

  if (loadingPositions) return (
    <div className="flex flex-col gap-4">
      {[...Array(3)].map((_, i) => <div key={i} className="card h-32 skeleton" />)}
    </div>
  )

  if (allPositions.length === 0) return (
    <EmptyState icon={PieChart} title="Nenhum ativo na carteira" description="Adicione lançamentos para visualizar a análise de concentração." />
  )

  return (
    <div className="flex flex-col gap-4">

      {/* Score HHI + header */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Score */}
        <div className="card p-5 flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <PieChart size={14} style={{ color: 'var(--color-primary)' }} />
            <span className="section-card-title">Score de Concentração</span>
          </div>
          <div style={{ fontSize: 'clamp(2rem, 4vw, 2.5rem)', fontWeight: 700, lineHeight: 1, color: hhiColor, fontVariantNumeric: 'tabular-nums' }}>
            {Math.round(hhi).toLocaleString('pt-BR')}
            <span style={{ fontSize: 'var(--text-sm)', fontWeight: 400, color: 'var(--color-text-muted)', marginLeft: 6 }}>HHI</span>
          </div>
          {/* Barra de progresso */}
          <div style={{ height: 6, borderRadius: 9999, background: 'var(--color-surface-dynamic)', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${hhiNorm * 100}%`, background: hhiColor, borderRadius: 9999, transition: 'width 600ms ease' }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            <span>0</span><span>2.500</span><span>10.000</span>
          </div>
          <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: hhiColor }}>{hhiLabel}</div>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)', lineHeight: 1.5 }}>
            O índice HHI mede concentração. Abaixo de 1.500 indica carteira bem diversificada.
          </p>
        </div>

        {/* Top 3 maiores posições */}
        <div className="card p-5 flex flex-col gap-3 md:col-span-2">
          <span className="section-card-title">Top 5 Posições</span>
          <div className="flex flex-col gap-2">
            {treemapByAsset.slice(0, 5).map((item, i) => {
              const total = treemapByAsset.reduce((s, x) => s + x.value, 0)
              const pct = total > 0 ? (item.value / total) * 100 : 0
              return (
                <div key={item.label} className="flex items-center gap-3">
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)', width: 16 }}>#{i + 1}</span>
                  <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', width: 72, flexShrink: 0 }}>{item.label}</span>
                  <div style={{ flex: 1, height: 6, borderRadius: 9999, background: 'var(--color-surface-dynamic)', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${pct}%`, background: item.color, borderRadius: 9999 }} />
                  </div>
                  <span style={{ fontSize: 'var(--text-xs)', tabularNums: true, color: 'var(--color-text-muted)', width: 48, textAlign: 'right' }}>{pct.toFixed(1)}%</span>
                  <span style={{ fontSize: 'var(--text-xs)', tabularNums: true, color: 'var(--color-text)', width: 88, textAlign: 'right' }}>{formatBRL(item.value)}</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Treemap */}
      <div className="card overflow-hidden">
        <div className="section-card-header" style={{ justifyContent: 'space-between' }}>
          <div className="flex items-center gap-2">
            <BarChart2 size={14} style={{ color: 'var(--color-primary)' }} />
            <span className="section-card-title">Mapa de Concentração</span>
          </div>
          <ToggleGroup<TreemapView>
            options={treemapViewOptions}
            value={treemapView}
            onChange={setTreemapView}
          />
        </div>
        <div className="p-4">
          <ConcentrationTreemap items={treemapView === 'ativo' ? treemapByAsset : treemapByClass} />
        </div>
        {/* Legenda */}
        <div className="px-4 pb-4 flex flex-wrap gap-2">
          {(treemapView === 'ativo' ? treemapByClass : treemapByClass).map(item => (
            <span key={item.label} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: item.color, flexShrink: 0 }} />
              {item.label}
            </span>
          ))}
        </div>
      </div>

      {/* Desvio do alvo */}
      {desvioRows.length > 0 ? (
        <div className="card overflow-hidden">
          <div className="section-card-header">
            <Target size={14} style={{ color: 'var(--color-primary)' }} />
            <span className="section-card-title">Desvio da Alocação Ideal</span>
          </div>
          <div className="overflow-x-auto">
            <table className="table-dense w-full">
              <thead>
                <tr>
                  <th>Classe</th>
                  <th className="text-right">Alvo</th>
                  <th className="text-right">Atual</th>
                  <th className="text-right">Desvio</th>
                  <th style={{ width: 160 }}>Barra</th>
                </tr>
              </thead>
              <tbody>
                {desvioRows.map((row: any) => {
                  const isOver  = row.delta > 0.5
                  const isUnder = row.delta < -0.5
                  const clr     = isOver ? 'var(--color-notification)' : isUnder ? 'var(--color-gold)' : 'var(--color-success)'
                  const Icon    = isOver ? ArrowUp : isUnder ? ArrowDown : Minus
                  const barPct  = Math.min(Math.abs(row.delta) / 20, 1) * 100
                  return (
                    <tr key={row.type}>
                      <td style={{ color: 'var(--color-text)' }}>
                        <span className="text-xs font-medium px-2 py-0.5 rounded border"
                          style={{
                            background: (ASSET_TYPE_COLORS[row.type] ?? FALLBACK_COLOR).bg,
                            color: (ASSET_TYPE_COLORS[row.type] ?? FALLBACK_COLOR).text,
                            borderColor: (ASSET_TYPE_COLORS[row.type] ?? FALLBACK_COLOR).border,
                          }}>
                          {row.label}
                        </span>
                      </td>
                      <td className="text-right tabular-nums" style={{ color: 'var(--color-text-muted)' }}>{row.target.toFixed(1)}%</td>
                      <td className="text-right tabular-nums" style={{ color: 'var(--color-text)' }}>{row.current.toFixed(1)}%</td>
                      <td className="text-right">
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontWeight: 600, fontSize: 'var(--text-xs)', color: clr }}>
                          <Icon size={11} />
                          {row.delta > 0 ? '+' : ''}{row.delta.toFixed(1)}%
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          {/* Barra divergente centralizada */}
                          <div style={{ flex: 1, height: 6, borderRadius: 9999, background: 'var(--color-surface-dynamic)', overflow: 'hidden', position: 'relative' }}>
                            <div style={{
                              position: 'absolute',
                              top: 0,
                              height: '100%',
                              width: `${barPct / 2}%`,
                              background: clr,
                              borderRadius: 9999,
                              left:  row.delta > 0 ? '50%'   : undefined,
                              right: row.delta < 0 ? '50%'   : undefined,
                            }} />
                          </div>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <div className="px-4 pb-3 pt-2 flex gap-4 flex-wrap" style={{ borderTop: '1px solid var(--color-divider)' }}>
            {[
              { color: 'var(--color-notification)', label: 'Acima do alvo' },
              { color: 'var(--color-gold)',          label: 'Abaixo do alvo' },
              { color: 'var(--color-success)',       label: 'No alvo (±0,5%)' },
            ].map(l => (
              <span key={l.label} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                <span style={{ width: 8, height: 8, borderRadius: 9999, background: l.color }} />
                {l.label}
              </span>
            ))}
          </div>
        </div>
      ) : (
        <div className="card p-6 flex items-center gap-3" style={{ color: 'var(--color-text-muted)' }}>
          <Target size={16} />
          <span className="text-sm">Configure metas de alocação em <a href="/carteira/metas" style={{ color: 'var(--color-primary)' }}>Configurações → Metas</a> para ver o desvio do alvo.</span>
        </div>
      )}
    </div>
  )
}

// ── Page root ────────────────────────────────────────────────────────────────────────────────────────
function PatrimonioPage() {
  const portfolioId = useAppStore(s => s.selectedPortfolioId)
  const [activeTab, setActiveTab] = useState<Tab>('visao-geral')

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

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Patrimônio</h1>
          <p className="page-subtitle">Visão consolidada e histórico da carteira selecionada</p>
        </div>
      </div>

      <TabBar active={activeTab} onChange={setActiveTab} />

      {activeTab === 'visao-geral'
        ? <TabVisaoGeral portfolioId={portfolioId} />
        : activeTab === 'historico'
          ? <TabHistorico  portfolioId={portfolioId} />
          : <TabAnalise    portfolioId={portfolioId} />}
    </div>
  )
}

export default PatrimonioPage
