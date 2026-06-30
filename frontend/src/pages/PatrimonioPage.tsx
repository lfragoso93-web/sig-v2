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
import clsx from 'clsx'

// ── Constantes ─────────────────────────────────────────────────────────────────
const ASSET_TYPE_LABELS: Record<string, string> = {
  ACAO: 'Ações', ACAO_NACIONAL: 'Ações', FII: 'FIIs',
  ETF_NACIONAL: 'ETFs BR', STOCK: 'Stocks', ETF_INTERNACIONAL: 'ETFs INT',
  TESOURO_DIRETO: 'Tesouro Direto', RENDA_FIXA: 'Renda Fixa', CRIPTO: 'Cripto',
  BDR: 'BDRs',
}

const ASSET_TYPE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  ACAO:              { bg: 'var(--color-blue-highlight)',    text: 'var(--color-blue)',    border: 'var(--color-blue-highlight)' },
  ACAO_NACIONAL:     { bg: 'var(--color-blue-highlight)',    text: 'var(--color-blue)',    border: 'var(--color-blue-highlight)' },
  FII:               { bg: 'var(--color-purple-highlight)',  text: 'var(--color-purple)',  border: 'var(--color-purple-highlight)' },
  ETF_NACIONAL:      { bg: 'var(--color-primary-highlight)', text: 'var(--color-primary)', border: 'var(--color-primary-highlight)' },
  STOCK:             { bg: 'var(--color-blue-highlight)',    text: 'var(--color-blue)',    border: 'var(--color-blue-highlight)' },
  ETF_INTERNACIONAL: { bg: 'var(--color-blue-highlight)',    text: 'var(--color-blue)',    border: 'var(--color-blue-highlight)' },
  TESOURO_DIRETO:    { bg: 'var(--color-gold-highlight)',    text: 'var(--color-gold)',    border: 'var(--color-gold-highlight)' },
  RENDA_FIXA:        { bg: 'var(--color-orange-highlight)',  text: 'var(--color-orange)',  border: 'var(--color-orange-highlight)' },
  CRIPTO:            { bg: 'var(--color-error-highlight)',   text: 'var(--color-error)',   border: 'var(--color-error-highlight)' },
  BDR:               { bg: 'var(--color-purple-highlight)',  text: 'var(--color-purple)',  border: 'var(--color-purple-highlight)' },
}
const FALLBACK_COLOR = { bg: 'var(--color-surface-dynamic)', text: 'var(--color-text-muted)', border: 'var(--color-border)' }

const CHART_COLORS: string[] = [
  'var(--color-blue)',
  'var(--color-primary)',
  'var(--color-gold)',
  'var(--color-notification)',
  'var(--color-purple)',
  'var(--color-orange)',
  'var(--color-success)',
  'var(--color-error)',
  '#3b82f6',
  '#6366f1',
]

const PERIODS: { label: string; value: PeriodOption }[] = [
  { label: '6m',   value: '6m'  },
  { label: '12m',  value: '12m' },
  { label: '24m',  value: '24m' },
  { label: 'Tudo', value: 'all' },
]

type ViewMode = 'diario' | 'mensal'

// ── Toggle group ───────────────────────────────────────────────────────────────
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

// ── Divisor de seção ───────────────────────────────────────────────────────────
function SectionDivider({ label, icon: Icon }: { label: string; icon?: React.ElementType }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.5rem' }}>
      {Icon && <Icon size={15} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />}
      <span style={{
        fontSize: 'var(--text-sm)', fontWeight: 700,
        letterSpacing: '-0.01em', color: 'var(--color-text)',
      }}>{label}</span>
      <div style={{ flex: 1, height: 1, background: 'oklch(from var(--color-text) l c h / 0.07)' }} />
    </div>
  )
}

// ── Gráfico de evolução ────────────────────────────────────────────────────────
function EvolucaoSection({ portfolioId }: { portfolioId: number }) {
  const [period, setPeriod] = useState<PeriodOption>('12m')
  const [view,   setView]   = useState<ViewMode>('mensal')
  const [backfillDone, setBackfillDone] = useState(false)

  const { data: daily,   isLoading: loadingDaily   } = useDailyEvolution(portfolioId, period)
  const { data: monthly, isLoading: loadingMonthly } = useMonthlyEvolution(portfolioId, period)
  const backfill = useEvolutionBackfill(portfolioId)

  const noData = view === 'mensal'
    ? (!loadingMonthly && (!monthly || monthly.length === 0))
    : (!loadingDaily   && (!daily   || daily.length   === 0))

  const viewOptions: { label: string; value: ViewMode }[] = [
    { label: 'Diário',  value: 'diario'  },
    { label: 'Mensal',  value: 'mensal'  },
  ]

  return (
    <div className="card">
      <div className="section-card-header" style={{ justifyContent: 'space-between' }}>
        <div className="flex items-center gap-2">
          {view === 'diario'
            ? <TrendingUp  size={14} style={{ color: 'var(--color-primary)' }} />
            : <BarChart2   size={14} style={{ color: 'var(--color-primary)' }} />}
          <span className="section-card-title">Evolução do Patrimônio</span>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <ToggleGroup<ViewMode>     options={viewOptions} value={view}   onChange={setView}   />
          <ToggleGroup<PeriodOption> options={PERIODS}     value={period} onChange={setPeriod} />
          <button
            onClick={async () => { await backfill.mutateAsync(); setBackfillDone(true); setTimeout(() => setBackfillDone(false), 3000) }}
            disabled={backfill.isPending}
            className="btn btn-ghost flex items-center gap-1.5 text-xs"
            title="Recalcular snapshots históricos"
          >
            <RefreshCw size={12} className={clsx(backfill.isPending && 'animate-spin')} />
            {backfillDone ? 'Atualizado!' : 'Atualizar'}
          </button>
        </div>
      </div>
      <div className="p-4">
        {noData ? (
          <div className="flex flex-col items-center gap-3 py-10" style={{ color: 'var(--color-text-muted)' }}>
            <AlertTriangle size={24} style={{ color: 'var(--color-warning, #f59e0b)' }} />
            <p className="text-sm text-center">
              Nenhum dado histórico.<br />
              Clique em <strong>Atualizar</strong> para gerar os snapshots.
            </p>
          </div>
        ) : view === 'diario' ? (
          loadingDaily   ? <div className="h-64 skeleton rounded" /> : <EvolutionLineChart data={daily ?? []} />
        ) : (
          loadingMonthly ? <div className="h-64 skeleton rounded" /> : <EvolutionBarChart  data={monthly ?? []} />
        )}
      </div>
    </div>
  )
}

// ── Consolidação por classe ────────────────────────────────────────────────────
function ConsolidacaoSection({
  portfolioId,
  onFilterChange,
  activeFilter,
}: {
  portfolioId: number
  onFilterChange: (t: string | null) => void
  activeFilter: string | null
}) {
  const { data: distribution, isLoading: loadingDist     } = useAssetDistribution(portfolioId)
  const { data: positions,    isLoading: loadingPositions } = usePositions(portfolioId)
  const { data: classTargets, isLoading: loadingTargets   } = useClassTargets(portfolioId)

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
      .map(([type, { total, count }]) => ({
        type, total, count,
        pct: grandTotal > 0 ? (total / grandTotal) * 100 : 0,
      }))
      .sort((a, b) => b.total - a.total)
  }, [allPositions])

  type ConsolTab = 'tipo' | 'ativos' | 'exterior'
  const [consolTab, setConsolTab] = useState<ConsolTab>('tipo')
  const consolTabs: { id: ConsolTab; label: string }[] = [
    { id: 'tipo',     label: 'Tipo de ativos' },
    { id: 'ativos',   label: 'Ativos' },
    { id: 'exterior', label: 'Exposição ao exterior' },
  ]

  const allAssetsSorted = useMemo(() => {
    const total = allPositions.reduce((s: number, p: any) => s + (p.current_value ?? 0), 0)
    return allPositions
      .filter((p: any) => (p.current_value ?? 0) > 0)
      .map((p: any, i: number) => ({
        label: p.ticker ?? p.asset_code ?? '?',
        type:  p.asset_type ?? 'OUTROS',
        value: p.current_value ?? 0,
        pct:   total > 0 ? ((p.current_value ?? 0) / total) * 100 : 0,
        color: CHART_COLORS[i % CHART_COLORS.length],
      }))
      .sort((a: any, b: any) => b.value - a.value)
  }, [allPositions])

  const exteriorTypes = ['STOCK', 'ETF_INTERNACIONAL', 'BDR', 'CRIPTO']
  const exteriorAssets = useMemo(() => {
    const total = allPositions.reduce((s: number, p: any) => s + (p.current_value ?? 0), 0)
    return allPositions
      .filter((p: any) => exteriorTypes.includes(p.asset_type) && (p.current_value ?? 0) > 0)
      .map((p: any, i: number) => ({
        label: p.ticker ?? p.asset_code ?? '?',
        type:  p.asset_type ?? 'OUTROS',
        value: p.current_value ?? 0,
        pct:   total > 0 ? ((p.current_value ?? 0) / total) * 100 : 0,
        color: CHART_COLORS[i % CHART_COLORS.length],
      }))
      .sort((a: any, b: any) => b.value - a.value)
  }, [allPositions])

  const donutData = useMemo(() => {
    if (consolTab === 'tipo') return distribution ?? []
    const items = consolTab === 'ativos' ? allAssetsSorted : exteriorAssets
    return items.map((it: any) => ({ name: it.label, value: it.value, color: it.color }))
  }, [consolTab, distribution, allAssetsSorted, exteriorAssets])

  const listItems = useMemo(() => {
    if (consolTab === 'tipo') return typeBreakdown.map((t, i) => ({
      label: ASSET_TYPE_LABELS[t.type] ?? t.type,
      type: t.type,
      value: t.total,
      pct: t.pct,
      color: CHART_COLORS[i % CHART_COLORS.length],
    }))
    const items = consolTab === 'ativos' ? allAssetsSorted : exteriorAssets
    return items.slice(0, 10)
  }, [consolTab, typeBreakdown, allAssetsSorted, exteriorAssets])

  return (
    <div className="card overflow-hidden">
      <div className="section-card-header" style={{ justifyContent: 'space-between' }}>
        <span className="section-card-title">Consolidação do patrimônio</span>
      </div>

      {/* Sub-tabs */}
      <div style={{ padding: '0 1rem 0', borderBottom: '1px solid var(--color-divider)' }}>
        <div className="flex gap-1">
          {consolTabs.map(t => (
            <button
              key={t.id}
              onClick={() => setConsolTab(t.id)}
              className="px-3 py-2 text-xs font-medium transition-colors"
              style={{
                borderBottom: consolTab === t.id ? '2px solid var(--color-primary)' : '2px solid transparent',
                color: consolTab === t.id ? 'var(--color-text)' : 'var(--color-text-muted)',
                background: 'transparent',
                marginBottom: -1,
              }}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-4">
        {loadingDist || loadingPositions ? (
          <div className="flex gap-8">
            <div className="skeleton w-48 h-48 rounded-full flex-shrink-0" />
            <div className="flex-1 flex flex-col gap-2">
              {[...Array(5)].map((_, i) => <div key={i} className="skeleton h-8 rounded" />)}
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
            {/* Donut */}
            <div className="flex justify-center">
              {donutData.length > 0
                ? <AssetDonutChart data={donutData} />
                : <div className="h-48 flex items-center justify-center text-xs" style={{ color: 'var(--color-text-muted)' }}>Sem dados</div>}
            </div>

            {/* Lista com barras horizontais */}
            <div className="flex flex-col">
              {listItems.length === 0 ? (
                <div className="h-48 flex items-center justify-center text-xs" style={{ color: 'var(--color-text-muted)' }}>
                  {consolTab === 'exterior' ? 'Nenhum ativo internacional' : 'Sem dados'}
                </div>
              ) : listItems.map((item, i) => (
                <button
                  key={item.label + i}
                  type="button"
                  onClick={() => consolTab === 'tipo' ? onFilterChange(activeFilter === item.type ? null : item.type) : undefined}
                  className="flex items-center gap-3 py-2.5 px-1 text-left transition-colors"
                  style={{
                    borderBottom: '1px solid var(--color-divider)',
                    background: consolTab === 'tipo' && activeFilter === item.type ? 'var(--color-surface-offset)' : 'transparent',
                    cursor: consolTab === 'tipo' ? 'pointer' : 'default',
                  }}
                >
                  <span
                    className="shrink-0 text-xs font-medium px-2 py-0.5 rounded"
                    style={{
                      background: consolTab === 'tipo'
                        ? (ASSET_TYPE_COLORS[item.type] ?? FALLBACK_COLOR).bg
                        : `${item.color}22`,
                      color: consolTab === 'tipo'
                        ? (ASSET_TYPE_COLORS[item.type] ?? FALLBACK_COLOR).text
                        : item.color,
                      minWidth: 80,
                      textAlign: 'center',
                    }}
                  >
                    {item.label}
                  </span>
                  <div
                    className="flex-1 h-1.5 rounded-full overflow-hidden"
                    style={{ background: 'var(--color-surface-dynamic)' }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${item.pct}%`, background: item.color, transition: 'width 500ms ease' }}
                    />
                  </div>
                  <span className="shrink-0 text-xs tabular-nums font-medium" style={{ color: 'var(--color-text)', width: 88, textAlign: 'right' }}>
                    {formatBRL(item.value)}
                  </span>
                  <span className="shrink-0 text-xs tabular-nums" style={{ color: 'var(--color-text-muted)', width: 44, textAlign: 'right' }}>
                    {item.pct.toFixed(2)}%
                  </span>
                </button>
              ))}
              {activeFilter && consolTab === 'tipo' && (
                <div className="pt-2 flex items-center justify-between">
                  <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                    Filtrado: <strong style={{ color: 'var(--color-text)' }}>{ASSET_TYPE_LABELS[activeFilter] ?? activeFilter}</strong>
                  </span>
                  <button onClick={() => onFilterChange(null)} className="text-xs flex items-center gap-1" style={{ color: 'var(--color-primary)' }}>
                    <RefreshCw size={11} /> Ver todos
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Distribuição Ideal vs. Atual */}
      {(classTargets && classTargets.length > 0) && (
        <div style={{ padding: '0 1rem 1rem', borderTop: '1px solid var(--color-divider)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '0.75rem 0 0.5rem' }}>
            <Target size={12} style={{ color: 'var(--color-primary)' }} />
            <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-muted)' }}>
              Distribuição Ideal vs. Atual
            </span>
          </div>
          {loadingTargets
            ? <div className="animate-pulse rounded-md" style={{ height: 80, background: 'var(--color-surface-offset)' }} />
            : <AllocationTargetWidget rows={classTargets} noTopMargin />}
        </div>
      )}
    </div>
  )
}

// ── Análise de concentração (inline, sem aba) ──────────────────────────────────
function AnaliseSection({ portfolioId }: { portfolioId: number }) {
  const { data: positions    } = usePositions(portfolioId)
  const { data: classTargets } = useClassTargets(portfolioId)

  const allPositions = useMemo(() => {
    if (!positions) return []
    return positions.flatMap((g: PositionGroup) => g.positions ?? [])
  }, [positions])

  const byClass = useMemo(() => {
    const map: Record<string, number> = {}
    for (const p of allPositions) {
      const t = p.asset_type ?? 'OUTROS'
      map[t] = (map[t] ?? 0) + (p.current_value ?? 0)
    }
    const total = Object.values(map).reduce((s, v) => s + v, 0)
    return Object.entries(map)
      .filter(([, v]) => v > 0)
      .map(([type, value], i) => ({
        type, value,
        label: ASSET_TYPE_LABELS[type] ?? type,
        pct: total > 0 ? (value / total) * 100 : 0,
        color: CHART_COLORS[i % CHART_COLORS.length],
      }))
      .sort((a, b) => b.value - a.value)
  }, [allPositions])

  const byAsset = useMemo(() => {
    const total = allPositions.reduce((s: number, p: any) => s + (p.current_value ?? 0), 0)
    return allPositions
      .filter((p: any) => (p.current_value ?? 0) > 0)
      .map((p: any, i: number) => ({
        label: p.ticker ?? p.asset_code ?? '?',
        type:  p.asset_type ?? 'OUTROS',
        value: p.current_value ?? 0,
        pct:   total > 0 ? ((p.current_value ?? 0) / total) * 100 : 0,
        color: CHART_COLORS[i % CHART_COLORS.length],
      }))
      .sort((a: any, b: any) => b.value - a.value)
  }, [allPositions])

  const { hhi, hhiNorm, hhiLevel, hhiLabel } = useMemo(() => {
    const total = byAsset.reduce((s, i) => s + i.value, 0)
    if (total === 0) return { hhi: 0, hhiNorm: 0, hhiLevel: 'neutro' as const, hhiLabel: '—' }
    const hhi = byAsset.reduce((s, i) => {
      const pct = (i.value / total) * 100
      return s + pct * pct
    }, 0)
    const hhiNorm = Math.min(hhi / 10000, 1)
    if (hhi < 1500) return { hhi, hhiNorm, hhiLevel: 'baixo'  as const, hhiLabel: 'Bem diversificado' }
    if (hhi < 2500) return { hhi, hhiNorm, hhiLevel: 'medio'  as const, hhiLabel: 'Concentração moderada' }
    return               { hhi, hhiNorm, hhiLevel: 'alto'   as const, hhiLabel: 'Alta concentração' }
  }, [byAsset])

  const hhiColor = hhiLevel === 'baixo' ? 'var(--color-success)'
    : hhiLevel === 'medio' ? 'var(--color-gold)'
    : hhiLevel === 'alto'  ? 'var(--color-error)'
    : 'var(--color-text-muted)'

  const desvioRows = useMemo(() => {
    if (!classTargets || classTargets.length === 0) return []
    return classTargets
      .map((row: any) => ({
        label:   ASSET_TYPE_LABELS[row.asset_class] ?? row.asset_class,
        type:    row.asset_class as string,
        target:  row.target_pct  as number,
        current: row.current_pct as number,
        delta:   (row.current_pct ?? 0) - (row.target_pct ?? 0),
      }))
      .sort((a: any, b: any) => Math.abs(b.delta) - Math.abs(a.delta))
  }, [classTargets])

  if (allPositions.length === 0) return null

  return (
    <div className="flex flex-col gap-4">

      {/* Score HHI + Top 5 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-5 flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <PieChart size={14} style={{ color: 'var(--color-primary)' }} />
            <span className="section-card-title">Score de Concentração</span>
          </div>
          <div style={{ fontSize: 'clamp(2rem, 4vw, 2.5rem)', fontWeight: 700, lineHeight: 1, color: hhiColor, fontVariantNumeric: 'tabular-nums' }}>
            {Math.round(hhi).toLocaleString('pt-BR')}
            <span style={{ fontSize: 'var(--text-sm)', fontWeight: 400, color: 'var(--color-text-muted)', marginLeft: 6 }}>HHI</span>
          </div>
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

        <div className="card p-5 flex flex-col gap-3 md:col-span-2">
          <span className="section-card-title">Top 5 Posições</span>
          <div className="flex flex-col gap-2">
            {byAsset.slice(0, 5).map((item, i) => (
              <div key={item.label} className="flex items-center gap-3">
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)', width: 20, textAlign: 'right' }}>#{i + 1}</span>
                <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', width: 72, flexShrink: 0 }}>{item.label}</span>
                <div style={{ flex: 1, height: 6, borderRadius: 9999, background: 'var(--color-surface-dynamic)', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${item.pct}%`, background: item.color, borderRadius: 9999, transition: 'width 500ms ease' }} />
                </div>
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', width: 44, textAlign: 'right' }}>{item.pct.toFixed(1)}%</span>
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text)', width: 88, textAlign: 'right' }}>{formatBRL(item.value)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Concentração por classe */}
      {byClass.map(cls => (
        <div key={cls.type} className="card overflow-hidden">
          <div className="section-card-header" style={{ justifyContent: 'space-between' }}>
            <span className="section-card-title">{cls.label}</span>
            <span
              className="text-xs font-medium px-2 py-0.5 rounded"
              style={{
                background: (ASSET_TYPE_COLORS[cls.type] ?? FALLBACK_COLOR).bg,
                color:      (ASSET_TYPE_COLORS[cls.type] ?? FALLBACK_COLOR).text,
              }}
            >
              {cls.pct.toFixed(1)}% da carteira
            </span>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
              <div className="flex justify-center">
                {(() => {
                  const classPositions = allPositions
                    .filter((p: any) => p.asset_type === cls.type && (p.current_value ?? 0) > 0)
                  const classTotal = classPositions.reduce((s: number, p: any) => s + (p.current_value ?? 0), 0)
                  const donutItems = classPositions
                    .map((p: any, i: number) => ({
                      name:  p.ticker ?? p.asset_code ?? '?',
                      value: p.current_value ?? 0,
                      color: CHART_COLORS[i % CHART_COLORS.length],
                    }))
                    .sort((a: any, b: any) => b.value - a.value)
                  return donutItems.length > 0
                    ? <AssetDonutChart data={donutItems} />
                    : <div className="h-40 flex items-center justify-center text-xs" style={{ color: 'var(--color-text-muted)' }}>Sem ativos</div>
                })()}
              </div>
              <div className="flex flex-col">
                {allPositions
                  .filter((p: any) => p.asset_type === cls.type && (p.current_value ?? 0) > 0)
                  .sort((a: any, b: any) => (b.current_value ?? 0) - (a.current_value ?? 0))
                  .map((p: any, i: number) => {
                    const classTotal = allPositions
                      .filter((pp: any) => pp.asset_type === cls.type)
                      .reduce((s: number, pp: any) => s + (pp.current_value ?? 0), 0)
                    const pct = classTotal > 0 ? ((p.current_value ?? 0) / classTotal) * 100 : 0
                    const color = CHART_COLORS[i % CHART_COLORS.length]
                    return (
                      <div key={p.ticker ?? i} className="flex items-center gap-3 py-2" style={{ borderBottom: '1px solid var(--color-divider)' }}>
                        <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', width: 72, flexShrink: 0 }}>
                          {p.ticker ?? p.asset_code ?? '?'}
                        </span>
                        <div style={{ flex: 1, height: 6, borderRadius: 9999, background: 'var(--color-surface-dynamic)', overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 9999, transition: 'width 500ms ease' }} />
                        </div>
                        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text)', width: 88, textAlign: 'right' }}>
                          {formatBRL(p.current_value ?? 0)}
                        </span>
                        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', width: 44, textAlign: 'right' }}>
                          {pct.toFixed(0)}%
                        </span>
                      </div>
                    )
                  })}
              </div>
            </div>
          </div>
        </div>
      ))}

      {/* Desvio do Alvo */}
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
                  const isOver  = row.delta >  0.5
                  const isUnder = row.delta < -0.5
                  const clr     = isOver ? 'var(--color-notification)' : isUnder ? 'var(--color-gold)' : 'var(--color-success)'
                  const Icon    = isOver ? ArrowUp : isUnder ? ArrowDown : Minus
                  const barPct  = Math.min(Math.abs(row.delta) / 20, 1) * 100
                  return (
                    <tr key={row.type}>
                      <td>
                        <span
                          className="text-xs font-medium px-2 py-0.5 rounded border"
                          style={{
                            background:  (ASSET_TYPE_COLORS[row.type] ?? FALLBACK_COLOR).bg,
                            color:       (ASSET_TYPE_COLORS[row.type] ?? FALLBACK_COLOR).text,
                            borderColor: (ASSET_TYPE_COLORS[row.type] ?? FALLBACK_COLOR).border,
                          }}
                        >
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
                        <div style={{ position: 'relative', height: 6, borderRadius: 9999, background: 'var(--color-surface-dynamic)', overflow: 'hidden' }}>
                          <div style={{
                            position: 'absolute', top: 0, height: '100%',
                            width: `${barPct / 2}%`, background: clr, borderRadius: 9999,
                            left:  row.delta > 0 ? '50%' : undefined,
                            right: row.delta < 0 ? '50%' : undefined,
                          }} />
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
              { color: 'var(--color-notification)', label: 'Acima do alvo'   },
              { color: 'var(--color-gold)',          label: 'Abaixo do alvo'  },
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
          <span className="text-sm">
            Configure metas de alocação em{' '}
            <a href="/carteira/metas" style={{ color: 'var(--color-primary)' }}>Configurações → Metas</a>
            {' '}para ver o desvio do alvo.
          </span>
        </div>
      )}
    </div>
  )
}

// ── Page root ──────────────────────────────────────────────────────────────────
function PatrimonioPage() {
  const portfolioId = useAppStore(s => s.selectedPortfolioId)
  const [activeTypeFilter, setActiveTypeFilter] = useState<string | null>(null)

  const { data: summary,   isLoading: loadingSummary   } = usePortfolioSummary(portfolioId ?? 0)
  const { data: positions, isLoading: loadingPositions } = usePositions(portfolioId ?? 0)

  const filteredPositions = useMemo(() => {
    if (!positions) return []
    if (!activeTypeFilter) return positions
    return positions
      .map((g: PositionGroup) => ({
        ...g,
        positions: g.positions.filter((p: any) => p.asset_type === activeTypeFilter),
      }))
      .filter((g: PositionGroup) => g.positions.length > 0)
  }, [positions, activeTypeFilter])

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
          <p className="page-subtitle">Visão consolidada da carteira selecionada</p>
        </div>
      </div>

      {/* ── KPIs ── */}
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

      {/* ── Evolução ── */}
      <EvolucaoSection portfolioId={portfolioId} />

      {/* ── Consolidação ── */}
      <ConsolidacaoSection
        portfolioId={portfolioId}
        onFilterChange={setActiveTypeFilter}
        activeFilter={activeTypeFilter}
      />

      {/* ── Posições ── */}
      <div className="card overflow-hidden">
        <div className="section-card-header" style={{ justifyContent: 'space-between' }}>
          <div className="flex items-center gap-2">
            <span className="section-card-title">Posições</span>
            {filteredPositions.length > 0 && (
              <span
                className="px-1.5 py-0.5 rounded text-xs tabular-nums"
                style={{ background: 'var(--color-surface-dynamic)', color: 'var(--color-text-muted)' }}
              >
                {filteredPositions.reduce((s: number, g: PositionGroup) => s + g.count, 0)}
              </span>
            )}
          </div>
          {activeTypeFilter && (
            <div className="flex items-center gap-2">
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                Filtrado: <strong style={{ color: 'var(--color-text)' }}>{ASSET_TYPE_LABELS[activeTypeFilter] ?? activeTypeFilter}</strong>
              </span>
              <button onClick={() => setActiveTypeFilter(null)} className="text-xs flex items-center gap-1" style={{ color: 'var(--color-primary)' }}>
                <RefreshCw size={11} /> Ver todos
              </button>
            </div>
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

      {/* ── Análise de Concentração ── */}
      <SectionDivider label="Análise de Concentração" icon={PieChart} />
      <AnaliseSection portfolioId={portfolioId} />

    </div>
  )
}

export default PatrimonioPage
