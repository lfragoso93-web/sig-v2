import { useState } from 'react'
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
  { label: '6 Meses', value: 6 },
  { label: '12 Meses', value: 12 },
  { label: '24 Meses', value: 24 },
  { label: 'Tudo', value: 60 },
]

export default function ResumePage() {
  const globalPortfolioId = useAppStore(s => s.selectedPortfolioId)
  const setGlobal         = useAppStore(s => s.setSelectedPortfolioId)

  const { data: portfolios, isLoading: loadingPortfolios } = usePortfolioList()
  const [period, setPeriod] = useState(12)

  // usa id global do store; fallback para o primeiro
  const portfolioId: number | null =
    globalPortfolioId ?? (portfolios?.[0]?.id ?? null)

  const { data: summary,          isLoading: loadingSummary   } = usePortfolioSummary(portfolioId)
  const { data: patrimonioHistory, isLoading: loadingHistory   } = usePatrimonioHistory(portfolioId, period)
  const { data: distribution,      isLoading: loadingDist      } = useAssetDistribution(portfolioId)
  const { data: positions,          isLoading: loadingPositions } = usePositions(portfolioId)

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

      {/* Portfolio selector */}
      {portfolios.length > 1 && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Carteira:</span>
          <div className="flex gap-1">
            {portfolios.map(p => (
              <button
                key={p.id}
                onClick={() => setGlobal(p.id)}
                className={clsx(
                  'px-3 py-1 rounded text-xs font-medium transition-colors',
                  portfolioId === p.id
                    ? 'bg-brand-600 text-white'
                    : 'bg-surface-800 border border-surface-600 text-slate-400 hover:bg-surface-700'
                )}
              >
                {p.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {loadingSummary ? (
          [...Array(4)].map((_, i) => <SkeletonCard key={i} />)
        ) : summary ? (
          <>
            <KpiCard
              label="Patrimônio total"
              value={formatBRL(summary.total_patrimonio ?? 0)}
              subValue={formatBRL(summary.total_investido ?? 0)}
              subLabel="Valor investido"
              change={summary.variacao_percentual}
            />
            <KpiCard
              label="Lucro total"
              value={formatBRL(summary.lucro_total ?? 0)}
              subLabel={`Ganho de Capital ${formatBRL(summary.ganho_capital ?? 0)} · Dividendos ${formatBRL(summary.dividendos_recebidos_12m ?? 0)}`}
            />
            <KpiCard
              label="Proventos Recebidos (12m)"
              value={formatBRL(summary.dividendos_recebidos_12m ?? 0)}
              subValue={formatBRL(summary.total_proventos ?? 0)}
              subLabel="Total"
            />
            <div className="rounded-xl bg-surface-900 border border-surface-700 p-4 flex flex-col gap-1">
              <span className="text-xs text-slate-500 font-medium">Variação / Rentabilidade</span>
              <div className={clsx('text-2xl font-bold tabular-nums tracking-tight', signClass(summary.variacao_valor ?? 0))}>
                {formatBRL(summary.variacao_valor ?? 0)}
              </div>
              <div className={clsx('text-xs font-medium', signClass(summary.variacao_valor ?? 0))}>
                {formatPercent(summary.variacao_percentual ?? 0)}
              </div>
              <div className={clsx('text-sm font-bold mt-1 tabular-nums', signClass(summary.rentabilidade_total ?? 0))}>
                {formatPercent(summary.rentabilidade_total ?? 0)}{' '}
                <span className="text-xs font-normal text-slate-500">rentabilidade</span>
              </div>
            </div>
          </>
        ) : (
          <div className="col-span-4 py-6 text-center text-xs text-slate-500">
            Nenhum dado. Adicione lançamentos para ver o resumo.
          </div>
        )}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="rounded-xl bg-surface-900 border border-surface-700 p-4 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <BarChart2 size={16} className="text-brand-500" />
              <span className="text-sm font-semibold text-slate-200">Evolução do Patrimônio</span>
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
                      : 'text-slate-500 hover:text-slate-300'
                  )}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          {loadingHistory ? (
            <div className="h-52 animate-pulse bg-surface-800 rounded" />
          ) : patrimonioHistory?.length ? (
            <PatrimonioBarChart data={patrimonioHistory} />
          ) : (
            <div className="h-52 flex items-center justify-center text-xs text-slate-500">Sem dados históricos ainda</div>
          )}
        </div>

        <div className="rounded-xl bg-surface-900 border border-surface-700 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Activity size={16} className="text-brand-500" />
            <span className="text-sm font-semibold text-slate-200">Ativos na Carteira</span>
          </div>
          {loadingDist ? (
            <div className="h-52 animate-pulse bg-surface-800 rounded" />
          ) : distribution?.length ? (
            <AssetDonutChart data={distribution} />
          ) : (
            <div className="h-52 flex items-center justify-center text-xs text-slate-500">Sem ativos</div>
          )}
        </div>
      </div>

      {/* Posições */}
      <div className="rounded-xl bg-surface-900 border border-surface-700 overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-3 border-b border-surface-700">
          <TrendingUp size={16} className="text-brand-500" />
          <span className="text-sm font-semibold text-slate-200">Meus Ativos</span>
          {positions && (
            <span className="ml-1 px-1.5 py-0.5 rounded bg-surface-700 text-slate-400 text-xs tabular-nums">
              {positions.reduce((acc, g) => acc + g.count, 0)}
            </span>
          )}
        </div>

        {loadingPositions ? (
          <div className="p-4 flex flex-col gap-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-10 animate-pulse bg-surface-800 rounded" />
            ))}
          </div>
        ) : positions?.length ? (
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
