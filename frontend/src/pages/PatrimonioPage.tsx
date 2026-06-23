import { useMemo, useState } from 'react'
import {
  BarChart2, RefreshCw, Wallet, TrendingUp, LineChart, AlertTriangle,
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
import { useAppStore } from '@/store/appStore'
import { formatBRL, formatPercent, signClass } from '@/utils/format'
import KpiCard from '@/components/ui/KpiCard'
import SkeletonCard from '@/components/ui/SkeletonCard'
import EmptyState from '@/components/ui/EmptyState'
import AssetDonutChart from '@/components/charts/AssetDonutChart'
import PositionTable from '@/components/resume/PositionTable'
import EvolutionLineChart from '@/components/charts/EvolutionLineChart'
import EvolutionBarChart from '@/components/charts/EvolutionBarChart'
import clsx from 'clsx'

// ── Constantes ────────────────────────────────────────────────────────────────

const ASSET_TYPE_LABELS: Record<string, string> = {
  ACAO: 'Ações', ACAO_NACIONAL: 'Ações', FII: 'FIIs',
  ETF_NACIONAL: 'ETFs BR', STOCK: 'Stocks', ETF_INTERNACIONAL: 'ETFs INT',
  TESOURO_DIRETO: 'Tesouro Direto', RENDA_FIXA: 'Renda Fixa', CRIPTO: 'Cripto',
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
}
const FALLBACK_COLOR = { bg: 'var(--color-surface-dynamic)', text: 'var(--color-text-muted)', border: 'var(--color-border)' }

const PERIODS: { label: string; value: PeriodOption }[] = [
  { label: '6m',   value: '6m'  },
  { label: '12m',  value: '12m' },
  { label: '24m',  value: '24m' },
  { label: 'Tudo', value: 'all' },
]

type Tab = 'visao-geral' | 'historico'
type ViewMode = 'diario' | 'mensal'

// ── Tab bar ───────────────────────────────────────────────────────────────────

function TabBar({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
    { id: 'visao-geral', label: 'Visão Geral', icon: BarChart2 },
    { id: 'historico',   label: 'Histórico',    icon: LineChart  },
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

// ── Aba: Visao Geral ──────────────────────────────────────────────────────────

function TabVisaoGeral({ portfolioId }: { portfolioId: number }) {
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

      {/* Breakdown por classe + donut */}
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

        {/* Donut */}
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

// ── Aba: Historico ────────────────────────────────────────────────────────────

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

  return (
    <>
      {/* Controles topo: periodo + backfill */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {/* Toggle diario / mensal */}
          <div
            className="flex rounded-lg overflow-hidden"
            style={{ border: '1px solid var(--color-border)', background: 'var(--color-surface)' }}
          >
            {(['diario', 'mensal'] as ViewMode[]).map(v => (
              <button
                key={v}
                onClick={() => setView(v)}
                className="px-4 py-1.5 text-xs font-medium transition-colors"
                style={{
                  background: view === v ? 'var(--color-primary)' : 'transparent',
                  color:      view === v ? '#fff' : 'var(--color-text-muted)',
                }}
              >
                {v === 'diario' ? 'Diário' : 'Mensal'}
              </button>
            ))}
          </div>

          {/* Seletor de periodo */}
          <div
            className="flex rounded-lg overflow-hidden"
            style={{ border: '1px solid var(--color-border)', background: 'var(--color-surface)' }}
          >
            {PERIODS.map(p => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                className="px-3 py-1.5 text-xs font-medium transition-colors"
                style={{
                  background: period === p.value ? 'var(--color-primary)' : 'transparent',
                  color:      period === p.value ? '#fff' : 'var(--color-text-muted)',
                }}
              >
                {p.label}
              </button>
            ))}
          </div>
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

      {/* KPIs do periodo */}
      <div className="kpi-grid">
        {loadingDaily ? (
          [...Array(4)].map((_, i) => <SkeletonCard key={i} />)
        ) : last ? (
          <>
            <KpiCard
              label="Valor atual (mercado)"
              value={formatBRL(last.market_value)}
              subValue={formatBRL(last.invested_total)}
              subLabel="Total investido"
            />
            <KpiCard
              label="Resultado total"
              value={formatBRL(last.total_pnl)}
              valueColor={signClass(last.total_pnl)}
              subLabel={`Realizado: ${formatBRL(last.realized_pnl)}`}
            />
            <KpiCard
              label={`Variação no período (${period})`}
              value={variacao !== null ? formatBRL(variacao) : '—'}
              valueColor={variacao !== null ? signClass(variacao) : undefined}
              change={variacaoPct ?? undefined}
            />
            <KpiCard
              label="Rentabilidade total"
              value={formatPercent(last.return_pct)}
              valueColor={signClass(last.return_pct)}
              subLabel="Sobre o capital investido"
            />
          </>
        ) : (
          <div className="col-span-4 py-8 text-center text-xs" style={{ color: 'var(--color-text-muted)' }}>
            Nenhum snapshot encontrado. Clique em “Atualizar histórico” para gerar os dados.
          </div>
        )}
      </div>

      {/* Grafico */}
      <div className="card overflow-hidden">
        <div className="section-card-header">
          {view === 'diario'
            ? <TrendingUp size={14} style={{ color: 'var(--color-primary)' }} />
            : <BarChart2  size={14} style={{ color: 'var(--color-primary)' }} />}
          <span className="section-card-title">
            {view === 'diario' ? 'Evolução Diária' : 'Evolução Mensal'}
          </span>
        </div>
        <div className="p-4">
          {noData ? (
            <div className="flex flex-col items-center gap-3 py-10" style={{ color: 'var(--color-text-muted)' }}>
              <AlertTriangle size={24} style={{ color: 'var(--color-warning, #f59e0b)' }} />
              <p className="text-sm text-center">
                Nenhum dado histórico encontrado.<br />
                Clique em <strong>Atualizar histórico</strong> acima para gerar os snapshots.
              </p>
            </div>
          ) : view === 'diario' ? (
            loadingDaily
              ? <div className="h-64 skeleton rounded" />
              : <EvolutionLineChart data={daily ?? []} />
          ) : (
            loadingMonthly
              ? <div className="h-64 skeleton rounded" />
              : <EvolutionBarChart data={monthly ?? []} />
          )}
        </div>
      </div>

      {/* Tabela resumo mensal */}
      {!loadingMonthly && monthly && monthly.length > 0 && (
        <div className="card overflow-hidden">
          <div className="section-card-header">
            <span className="section-card-title">Resumo Mensal</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-divider)', color: 'var(--color-text-muted)' }}>
                  <th className="px-4 py-2 text-left font-medium">Mês</th>
                  <th className="px-4 py-2 text-right font-medium">Valor mercado</th>
                  <th className="px-4 py-2 text-right font-medium">Investido</th>
                  <th className="px-4 py-2 text-right font-medium">P&amp;L não realiz.</th>
                  <th className="px-4 py-2 text-right font-medium">Rentab.</th>
                </tr>
              </thead>
              <tbody>
                {[...monthly].reverse().map((row, i) => (
                  <tr
                    key={row.period}
                    style={{
                      borderBottom: i < monthly.length - 1 ? '1px solid var(--color-divider)' : 'none',
                      background:   i === 0 ? 'var(--color-surface-offset)' : 'transparent',
                    }}
                  >
                    <td className="px-4 py-2.5" style={{ color: 'var(--color-text)' }}>
                      {row.period}
                      {i === 0 && (
                        <span
                          className="ml-2 text-xs px-1 py-0.5 rounded"
                          style={{ background: 'var(--color-primary-highlight)', color: 'var(--color-primary)', fontSize: 10 }}
                        >
                          atual
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums" style={{ color: 'var(--color-text)' }}>
                      {formatBRL(row.value)}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums" style={{ color: 'var(--color-text-muted)' }}>
                      {formatBRL(row.invested)}
                    </td>
                    <td className={clsx('px-4 py-2.5 text-right tabular-nums', signClass(row.unrealized_pnl))}>
                      {row.unrealized_pnl >= 0 ? '+' : ''}{formatBRL(row.unrealized_pnl)}
                    </td>
                    <td className={clsx('px-4 py-2.5 text-right tabular-nums font-medium', signClass(row.return_pct))}>
                      {row.return_pct >= 0 ? '+' : ''}{formatPercent(row.return_pct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  )
}

// ── Page root ─────────────────────────────────────────────────────────────────

export default function PatrimonioPage() {
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
      {/* Cabeçalho */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Patrimônio</h1>
          <p className="page-subtitle">Visão consolidada e histórico da carteira selecionada</p>
        </div>
      </div>

      {/* Tab bar */}
      <TabBar active={activeTab} onChange={setActiveTab} />

      {/* Conteudo da aba ativa */}
      {activeTab === 'visao-geral'
        ? <TabVisaoGeral portfolioId={portfolioId} />
        : <TabHistorico  portfolioId={portfolioId} />}
    </div>
  )
}
