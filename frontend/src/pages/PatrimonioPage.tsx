import { useMemo, useState } from 'react'
import { BarChart2, Wallet, Target, TrendingUp, PieChart } from 'lucide-react'
import {
  usePortfolioSummary,
  useAssetDistribution,
  usePositions,
  type PositionGroup,
} from '@/hooks/usePortfolio'
import {
  useDailyEvolution,
  useMonthlyEvolution,
  type PeriodOption,
} from '@/hooks/useEvolution'
import { useClassTargets } from '@/hooks/useClassTargets'
import { useAppStore } from '@/store/appStore'
import { formatBRL, formatPercent, signClass } from '@/utils/format'
import {
  formatReferenceDate,
  getPortfolioReturnPresentation,
  mapPortfolioSummaryMetrics,
} from '@/utils/portfolioSummary'
import KpiCard from '@/components/ui/KpiCard'
import SkeletonCard from '@/components/ui/SkeletonCard'
import EmptyState from '@/components/ui/EmptyState'
import AssetDonutChart from '@/components/charts/AssetDonutChart'
import AllocationTargetWidget from '@/components/resume/AllocationTargetWidget'
import EvolutionLineChart from '@/components/charts/EvolutionLineChart'
import EvolutionBarChart from '@/components/charts/EvolutionBarChart'

function safeNum(value: unknown): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function positionValue(position: { current_value?: number | null; invested_value?: number | null }): number {
  return position.current_value == null
    ? safeNum(position.invested_value)
    : safeNum(position.current_value)
}

const PERIODS: { label: string; value: PeriodOption }[] = [
  { label: '6m', value: '6m' },
  { label: '12m', value: '12m' },
  { label: '24m', value: '24m' },
  { label: 'Tudo', value: 'all' },
]

type ViewMode = 'diario' | 'mensal'

function ToggleGroup<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { label: string; value: T }[]
  value: T
  onChange: (value: T) => void
}) {
  return (
    <div className="flex" style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)' }}>
      {options.map(option => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className="px-3 py-1.5 text-xs font-medium transition-colors"
          style={{
            background: value === option.value ? 'var(--color-primary)' : 'transparent',
            color: value === option.value ? '#fff' : 'var(--color-text-muted)',
          }}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

function EvolutionSection({ portfolioId }: { portfolioId: number }) {
  const [period, setPeriod] = useState<PeriodOption>('12m')
  const [view, setView] = useState<ViewMode>('mensal')
  const { data: daily, isLoading: loadingDaily } = useDailyEvolution(portfolioId, period)
  const { data: monthly, isLoading: loadingMonthly } = useMonthlyEvolution(portfolioId, period)
  const data = view === 'mensal' ? monthly : daily
  const loading = view === 'mensal' ? loadingMonthly : loadingDaily

  return (
    <div className="card">
      <div className="section-card-header" style={{ justifyContent: 'space-between' }}>
        <div className="flex items-center gap-2">
          {view === 'diario'
            ? <TrendingUp size={14} style={{ color: 'var(--color-primary)' }} />
            : <BarChart2 size={14} style={{ color: 'var(--color-primary)' }} />}
          <div>
            <span className="section-card-title">Evolução do Patrimônio</span>
            <p className="text-xs mt-1" style={{ color: 'var(--color-text-faint)' }}>
              Fechamentos canônicos; não representa o valuation intradiário dos cards.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <ToggleGroup<ViewMode>
            options={[{ label: 'Diário', value: 'diario' }, { label: 'Mensal', value: 'mensal' }]}
            value={view}
            onChange={setView}
          />
          <ToggleGroup<PeriodOption> options={PERIODS} value={period} onChange={setPeriod} />
        </div>
      </div>
      <div className="p-4">
        {loading ? (
          <div className="h-64 skeleton rounded" />
        ) : !data?.length ? (
          <div className="h-64 flex items-center justify-center text-sm" style={{ color: 'var(--color-text-muted)' }}>
            Nenhum snapshot para o período selecionado.
          </div>
        ) : view === 'diario' ? (
          <EvolutionLineChart data={daily ?? []} />
        ) : (
          <EvolutionBarChart data={monthly ?? []} />
        )}
      </div>
    </div>
  )
}

function ConsolidationSection({ portfolioId }: { portfolioId: number }) {
  const { data: distribution, isLoading: loadingDistribution } = useAssetDistribution(portfolioId)
  const { data: groups, isLoading: loadingPositions } = usePositions(portfolioId)
  const { data: classTargets, isLoading: loadingTargets } = useClassTargets(portfolioId)

  const counts = useMemo(() => {
    const result: Record<string, number> = {}
    for (const group of groups ?? []) {
      const assetType = group.positions?.[0]?.asset_type
      if (assetType) result[assetType] = group.count
    }
    return result
  }, [groups])

  return (
    <div className="card overflow-hidden">
      <div className="section-card-header">
        <div>
          <span className="section-card-title">Consolidação do patrimônio</span>
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-faint)' }}>
            Distribuição calculada pelo valuation intradiário canônico.
          </p>
        </div>
      </div>
      <div className="p-5 md:p-6">
        {loadingDistribution || loadingPositions ? (
          <div className="h-56 skeleton rounded" />
        ) : !distribution?.length ? (
          <div className="h-56 flex items-center justify-center text-sm" style={{ color: 'var(--color-text-muted)' }}>
            Sem posições para consolidar.
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-8 items-center">
            <div className="flex justify-center">
              <AssetDonutChart data={distribution} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {distribution.map(item => (
                <div
                  key={item.asset_type}
                  className="rounded-xl p-4"
                  style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-divider)' }}
                >
                  <div className="flex items-center justify-between gap-3 mb-3">
                    <span className="text-xs font-semibold" style={{ color: item.color ?? 'var(--color-primary)' }}>
                      {item.label}
                    </span>
                    <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                      {counts[item.asset_type] ?? 0} ativo{(counts[item.asset_type] ?? 0) === 1 ? '' : 's'}
                    </span>
                  </div>
                  <div className="flex items-end justify-between gap-3">
                    <span className="text-sm font-semibold tabular-nums">{formatBRL(item.value)}</span>
                    <span className="text-sm font-semibold tabular-nums" style={{ color: 'var(--color-primary)' }}>
                      {item.percentage.toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      {!!classTargets?.length && (
        <div style={{ padding: '0 1.5rem 1.5rem', borderTop: '1px solid var(--color-divider)' }}>
          <div className="flex items-center gap-2 py-4">
            <Target size={13} style={{ color: 'var(--color-primary)' }} />
            <span className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
              Distribuição ideal versus atual
            </span>
          </div>
          {loadingTargets
            ? <div className="h-20 skeleton rounded" />
            : <AllocationTargetWidget rows={classTargets} noTopMargin />}
        </div>
      )}
    </div>
  )
}

function ConcentrationSection({ groups }: { groups: PositionGroup[] }) {
  const positions = useMemo(() => groups.flatMap(group => group.positions ?? []), [groups])
  const ranked = useMemo(() => {
    const total = positions.reduce((sum, position) => sum + positionValue(position), 0)
    return positions
      .map(position => ({
        ticker: position.ticker,
        value: positionValue(position),
        percentage: total > 0 ? positionValue(position) / total * 100 : 0,
      }))
      .filter(item => item.value > 0)
      .sort((a, b) => b.value - a.value)
  }, [positions])

  const hhi = ranked.reduce((sum, item) => sum + item.percentage ** 2, 0)
  const label = hhi < 1500 ? 'Bem diversificado' : hhi < 2500 ? 'Concentração moderada' : 'Alta concentração'
  const color = hhi < 1500 ? 'var(--color-success)' : hhi < 2500 ? 'var(--color-gold)' : 'var(--color-error)'

  if (!ranked.length) return null

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div className="card p-5 flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <PieChart size={14} style={{ color: 'var(--color-primary)' }} />
          <span className="section-card-title">Concentração</span>
        </div>
        <div className="text-3xl font-bold tabular-nums" style={{ color }}>{Math.round(hhi).toLocaleString('pt-BR')}</div>
        <div className="text-sm font-semibold" style={{ color }}>{label}</div>
        <p className="text-xs" style={{ color: 'var(--color-text-faint)' }}>Índice HHI calculado sobre o valuation intradiário das posições.</p>
      </div>
      <div className="card p-5 md:col-span-2">
        <span className="section-card-title">Top 5 posições</span>
        <div className="flex flex-col gap-3 mt-4">
          {ranked.slice(0, 5).map((item, index) => (
            <div key={item.ticker} className="flex items-center gap-3">
              <span className="text-xs" style={{ color: 'var(--color-text-faint)' }}>#{index + 1}</span>
              <span className="text-sm font-semibold w-20">{item.ticker}</span>
              <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--color-surface-dynamic)' }}>
                <div className="h-full rounded-full" style={{ width: `${Math.min(item.percentage, 100)}%`, background: 'var(--color-primary)' }} />
              </div>
              <span className="text-xs w-14 text-right tabular-nums">{item.percentage.toFixed(1)}%</span>
              <span className="text-xs w-24 text-right tabular-nums">{formatBRL(item.value)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function PatrimonioPage() {
  const portfolioId = useAppStore(state => state.selectedPortfolioId)
  const { data: summary, isLoading: loadingSummary, error: summaryError } = usePortfolioSummary(portfolioId ?? 0)
  const metrics = summary ? mapPortfolioSummaryMetrics(summary) : null
  const returnPresentation = getPortfolioReturnPresentation(metrics)
  const summaryContractError = summaryError instanceof Error
    && summaryError.message.startsWith('Contrato summary.v2 inválido:')
  const { data: groups = [] } = usePositions(portfolioId ?? 0)

  if (!portfolioId) {
    return (
      <div className="p-6">
        <EmptyState icon={Wallet} title="Nenhuma carteira selecionada" description="Selecione uma carteira no menu superior para visualizar o patrimônio." />
      </div>
    )
  }

  const valuationReference = formatReferenceDate(metrics?.valuationUpdatedAt)
  const performanceReference = formatReferenceDate(metrics?.performanceAsOf)
  const proventosReference = formatReferenceDate(metrics?.proventosAsOf)

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Patrimônio</h1>
          <p className="page-subtitle">Valuation intradiário e evolução por snapshots fechados</p>
        </div>
      </div>

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
              bottomLine={returnPresentation.isEstimated ? (
                <span className="text-xs font-semibold" style={{ color: 'var(--color-warning)' }}>
                  Estimativa do valuation atual; TWR indisponível sem snapshot
                </span>
              ) : undefined}
            />
          </>
        ) : (
          <div className="col-span-4 py-8 text-center text-xs" style={{ color: 'var(--color-text-muted)' }}>
            Nenhum dado disponível.
          </div>
        )}
      </div>

      {summary && metrics && (
        <div className="card px-4 py-3 flex flex-wrap gap-x-6 gap-y-2 text-xs" style={{ color: 'var(--color-text-muted)' }}>
          <span>Patrimônio e posições: {valuationReference ?? 'sem horário de cotação'}</span>
          <span>TWR até: {performanceReference ?? 'sem snapshot fechado'}{metrics.returnIsEstimated ? ' (estimado)' : ''}</span>
          <span>Proventos até: {proventosReference ?? '—'}</span>
          <span>Cobertura de preços: {safeNum(summary.price_coverage_pct).toFixed(1)}%</span>
        </div>
      )}

      <EvolutionSection portfolioId={portfolioId} />
      <ConsolidationSection portfolioId={portfolioId} />
      <ConcentrationSection groups={groups} />
    </div>
  )
}
