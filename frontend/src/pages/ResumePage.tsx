import { useState, useEffect } from 'react'
import { BarChart2, TrendingUp, DollarSign, Activity, PackageOpen, Briefcase } from 'lucide-react'
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
import CreatePortfolioModal from '@/components/modals/CreatePortfolioModal'

const PERIOD_OPTIONS = [
  { label: '6M',   value: 6  },
  { label: '12M',  value: 12 },
  { label: '24M',  value: 24 },
  { label: 'Tudo', value: 60 },
]

export default function ResumePage() {
  const globalPortfolioId = useAppStore(s => s.selectedPortfolioId)
  const setGlobal         = useAppStore(s => s.setSelectedPortfolioId)
  const [period, setPeriod]           = useState(12)
  const [showCreateModal, setShowCreateModal] = useState(false)

  const { data: portfolios, isLoading: loadingPortfolios } = usePortfolioList()

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

  const s = summary as any
  const patrimonio    = s?.total_patrimonio    ?? s?.current_value   ?? 0
  const investido     = s?.total_investido     ?? s?.total_invested  ?? 0
  const lucroTotal    = s?.lucro_total         ?? s?.total_gain      ?? 0
  const ganhoCapital  = s?.ganho_capital       ?? s?.total_gain      ?? 0
  const dividendos12m = s?.dividendos_recebidos_12m ?? 0
  const totalProv     = s?.total_proventos     ?? 0
  const variacaoVal   = s?.variacao_valor      ?? s?.total_gain      ?? 0
  const variacaoPct   = s?.variacao_percentual ?? s?.total_gain_pct  ?? 0
  const rentabilidade = s?.rentabilidade_total ?? s?.total_gain_pct  ?? 0

  if (loadingPortfolios) {
    return (
      <div className="page-container">
        <div className="kpi-grid">
          {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      </div>
    )
  }

  if (!portfolios?.length) {
    return (
      <div className="page-container">
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          minHeight: '60vh',
        }}>
          <EmptyState
            icon={Briefcase}
            title="Você ainda não tem uma carteira"
            description="Crie sua primeira carteira para começar a registrar e acompanhar seus investimentos."
            action={{ label: '+ Criar minha carteira', onClick: () => setShowCreateModal(true) }}
          />
        </div>

        {showCreateModal && (
          <CreatePortfolioModal onClose={() => setShowCreateModal(false)} />
        )}
      </div>
    )
  }

  return (
    <div className="page-container">

      {/* KPI Cards */}
      <div className="kpi-grid">
        {loadingSummary ? (
          [...Array(4)].map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <KpiCard
              label="Patrimônio Total"
              value={formatBRL(patrimonio)}
              subValue={formatBRL(investido)}
              subLabel="Valor investido"
              change={variacaoPct}
            />
            <KpiCard
              label="Resultado"
              value={formatBRL(lucroTotal)}
              valueColor={signClass(lucroTotal)}
              subLabel={`Capital ${formatBRL(ganhoCapital)} · Prov. ${formatBRL(totalProv)}`}
              bottomLine={
                <span className={clsx('text-xs font-semibold tabular-nums', signClass(rentabilidade))}>
                  {rentabilidade >= 0 ? '+' : ''}{formatPercent(rentabilidade)} rentab.
                </span>
              }
            />
            <KpiCard
              label="Proventos (12m)"
              value={formatBRL(dividendos12m)}
              subValue={formatBRL(totalProv)}
              subLabel="Total acumulado"
            />
            <KpiCard
              label="Variação"
              value={formatBRL(variacaoVal)}
              valueColor={signClass(variacaoVal)}
              change={variacaoPct}
              bottomLine={
                <span className={clsx('text-xs font-semibold tabular-nums', signClass(rentabilidade))}>
                  {rentabilidade >= 0 ? '+' : ''}{formatPercent(rentabilidade)} total
                </span>
              }
            />
          </>
        )}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card p-4 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <BarChart2 size={14} style={{ color: 'var(--color-primary)' }} />
              <span className="section-card-title">Evolução do Patrimônio</span>
            </div>
            <div className="flex gap-0.5">
              {PERIOD_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setPeriod(opt.value)}
                  className="px-2.5 py-1 rounded text-xs font-medium transition-colors"
                  style={{
                    background: period === opt.value ? 'oklch(from var(--color-primary) l c h / 0.15)' : 'transparent',
                    color: period === opt.value ? 'var(--color-primary)' : 'var(--color-text-muted)',
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          {loadingHistory ? (
            <div className="h-52 animate-pulse rounded-lg" style={{ background: 'var(--color-surface-offset)' }} />
          ) : patrimonioHistory?.length ? (
            <PatrimonioBarChart data={patrimonioHistory} />
          ) : (
            <div className="h-52 flex items-center justify-center text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Sem dados históricos ainda
            </div>
          )}
        </div>

        <div className="card p-4">
          <div className="flex items-center gap-2 mb-4">
            <Activity size={14} style={{ color: 'var(--color-primary)' }} />
            <span className="section-card-title">Distribuição</span>
          </div>
          {loadingDist ? (
            <div className="h-52 animate-pulse rounded-lg" style={{ background: 'var(--color-surface-offset)' }} />
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
        <div className="section-card-header">
          <TrendingUp size={14} style={{ color: 'var(--color-primary)' }} />
          <span className="section-card-title">Meus Ativos</span>
          {positions && (
            <span
              className="px-1.5 py-0.5 rounded text-xs tabular-nums"
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
