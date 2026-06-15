import { useState, useEffect } from 'react'
import { BarChart2, TrendingUp, DollarSign, Activity, PackageOpen } from 'lucide-react'
import clsx from 'clsx'
import {
  usePortfolioList,
  usePortfolioSummary,
  usePatrimonioHistory,
  useAssetDistribution,
  usePositions,
} from '@/hooks/usePortfolio'
import { useAppStore } from '@/store/appStore'
import { formatBRL, formatPercent, signClass } from '@/utils/format'
import KpiCard from '@/components/ui/KpiCard'
import SkeletonCard from '@/components/ui/SkeletonCard'
import EmptyState from '@/components/ui/EmptyState'
import PatrimonioBarChart from '@/components/charts/PatrimonioBarChart'
import AssetDonutChart from '@/components/charts/AssetDonutChart'
import PositionTable from '@/components/resume/PositionTable'

const PERIOD_OPTIONS = [
  { label: '6 Meses',  value: 6  },
  { label: '12 Meses', value: 12 },
  { label: '24 Meses', value: 24 },
  { label: 'Tudo',     value: 60 },
]

export default function ResumePage() {
  const globalPortfolioId = useAppStore(s => s.selectedPortfolioId)
  const setGlobal         = useAppStore(s => s.setSelectedPortfolioId)

  const { data: portfolios, isLoading: loadingPortfolios } = usePortfolioList()
  const [period, setPeriod] = useState(12)

  useEffect(() => {
    if (!globalPortfolioId && portfolios && portfolios.length > 0) {
      setGlobal(portfolios[0].id)
    }
  }, [globalPortfolioId, portfolios, setGlobal])

  const portfolioId: number | null = globalPortfolioId ?? (portfolios?.[0]?.id ?? null)

  const { data: summary,           isLoading: loadingSummary  } = usePortfolioSummary(portfolioId)
  const { data: patrimonioHistory, isLoading: loadingHistory   } = usePatrimonioHistory(portfolioId, period)
  const { data: distribution,      isLoading: loadingDist      } = useAssetDistribution(portfolioId)
  const { data: positions,         isLoading: loadingPositions } = usePositions(portfolioId)

  const safeGanhoCapital = (summary as any)?.ganho_capital ?? summary?.lucro_total ?? 0

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
          description="Crie sua primeira carteira para começar a registrar seus investimentos."
        />
      </div>
    )
  }

  return (
    <div className="p-4 md:p-6 flex flex-col gap-5 max-w-[1400px] mx-auto">

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {loadingSummary ? (
          [...Array(4)].map((_, i) => <SkeletonCard key={i} />)
        ) : summary ? (
          <>
            {/* 1 - Patrimônio total */}
            <KpiCard
              label="Patrimônio total"
              value={formatBRL(summary.total_patrimonio ?? 0)}
              subValue={formatBRL(summary.total_investido ?? 0)}
              subLabel="Valor investido"
              change={summary.variacao_percentual}
            />

            {/* 2 - Lucro total */}
            <KpiCard
              label="Lucro total"
              value={formatBRL(summary.lucro_total ?? 0)}
              subLabel={`Ganho de Capital ${formatBRL(safeGanhoCapital)} · Dividendos ${formatBRL(summary.dividendos_recebidos_12m ?? 0)}`}
            />

            {/* 3 - Proventos */}
            <KpiCard
              label="Proventos Recebidos (12m)"
              value={formatBRL(summary.dividendos_recebidos_12m ?? 0)}
              subValue={formatBRL(summary.total_proventos ?? 0)}
              subLabel="Total"
            />

            {/* 4 - Variação / Rentabilidade */}
            <div className="card p-4 flex flex-col gap-1">
              <span className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
                Variação / Rentabilidade
              </span>
              <div className={clsx('text-2xl font-bold tabular-nums tracking-tight', signClass(summary.variacao_valor ?? 0))}>
                {formatBRL(summary.variacao_valor ?? 0)}
              </div>
              <div className={clsx('text-xs font-semibold tabular-nums', signClass(summary.variacao_percentual ?? 0))}>
                {(summary.variacao_percentual ?? 0) >= 0 ? '+' : ''}{formatPercent(summary.variacao_percentual ?? 0)}
              </div>
              <div className={clsx('text-sm font-bold mt-1 tabular-nums', signClass(summary.rentabilidade_total ?? 0))}>
                {(summary.rentabilidade_total ?? 0) >= 0 ? '+' : ''}{formatPercent(summary.rentabilidade_total ?? 0)}{' '}
                <span className="text-xs font-normal" style={{ color: 'var(--color-text-faint)' }}>rentabilidade</span>
              </div>
            </div>
          </>
        ) : (
          <div className="col-span-4 py-6 text-center text-xs" style={{ color: 'var(--color-text-muted)' }}>
            Nenhum dado. Adicione lançamentos para ver o resumo.
          </div>
        )}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Evolução do Patrimônio */}
        <div className="card p-4 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <BarChart2 size={16} className="text-brand-400" />
              <span className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                Evolução do Patrimônio
              </span>
            </div>
            <div className="flex gap-1">
              {PERIOD_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setPeriod(opt.value)}
                  className={clsx(
                    'px-2.5 py-1 rounded text-xs font-medium transition-colors',
                    period === opt.value
                      ? 'bg-brand-600/20 text-brand-400'
                      : 'hover:text-brand-400'
                  )}
                  style={period !== opt.value ? { color: 'var(--color-text-muted)' } : {}}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          {loadingHistory ? (
            <div className="h-52 animate-pulse rounded" style={{ background: 'var(--color-surface-offset)' }} />
          ) : patrimonioHistory?.length ? (
            <PatrimonioBarChart data={patrimonioHistory} />
          ) : (
            <div className="h-52 flex items-center justify-center text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Sem dados históricos ainda
            </div>
          )}
        </div>

        {/* Ativos na Carteira */}
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-4">
            <Activity size={16} className="text-brand-400" />
            <span className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
              Ativos na Carteira
            </span>
          </div>
          {loadingDist ? (
            <div className="h-52 animate-pulse rounded" style={{ background: 'var(--color-surface-offset)' }} />
          ) : distribution?.length ? (
            <AssetDonutChart data={distribution} />
          ) : (
            <div className="h-52 flex items-center justify-center text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Sem ativos
            </div>
          )}
        </div>
      </div>

      {/* Posições */}
      <div className="card overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-3" style={{ borderBottom: '1px solid var(--color-border)' }}>
          <TrendingUp size={16} className="text-brand-400" />
          <span className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>Meus Ativos</span>
          {positions && (
            <span
              className="ml-1 px-1.5 py-0.5 rounded text-xs tabular-nums"
              style={{ background: 'var(--color-surface-offset)', color: 'var(--color-text-muted)' }}
            >
              {positions.reduce((acc, g) => acc + (g.count ?? 0), 0)}
            </span>
          )}
        </div>

        {loadingPositions ? (
          <div className="p-4 flex flex-col gap-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-10 animate-pulse rounded" style={{ background: 'var(--color-surface-offset)' }} />
            ))}
          </div>
        ) : positions && positions.length > 0 ? (
          <PositionTable groups={positions} />
        ) : (
          <EmptyState
            icon={DollarSign}
            title="Nenhum ativo encontrado"
            description="Adicione um lançamento para começar a acompanhar sua carteira."
          />
        )}
      </div>
    </div>
  )
}
