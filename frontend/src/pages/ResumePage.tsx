import { useState, useEffect } from 'react'
import { BarChart2, TrendingUp, DollarSign, Briefcase, AlertTriangle } from 'lucide-react'
import {
  usePortfolioList,
  usePositions,
  usePortfolioSummaryData,
} from '@/hooks/usePortfolio'
import {
  useClassMonthlyEvolution,
  useClassTwrAvailability,
  useMonthlyEvolution,
} from '@/hooks/useEvolution'
import type { PeriodOption } from '@/hooks/useEvolution'
import { useAppStore } from '@/store/appStore'
import { formatBRL, formatPercent, signClass } from '@/utils/format'
import { mapPortfolioSummaryMetrics } from '@/utils/portfolioSummary'
import KpiCard from '@/components/ui/KpiCard'
import SkeletonCard from '@/components/ui/SkeletonCard'
import EmptyState from '@/components/ui/EmptyState'
import PatrimonioBarChart from '@/components/charts/PatrimonioBarChart'
import PositionTable from '@/components/resume/PositionTable'
import CreatePortfolioModal from '@/components/modals/CreatePortfolioModal'

const PERIOD_OPTIONS = [
  { label: 'Últimos 6 meses', value: '6m' },
  { label: 'Últimos 12 meses', value: '12m' },
  { label: 'Últimos 24 meses', value: '24m' },
  { label: 'Todo período', value: 'all' },
]

const ASSET_CLASS_ALL = 'all'
const ASSET_CLASS_OPTIONS = [
  { label: 'Todas as classes',     value: ASSET_CLASS_ALL     },
  { label: 'Ações',               value: 'ACAO'              },
  { label: 'FIIs',                 value: 'FII'               },
  { label: 'ETF Nacional',         value: 'ETF_NACIONAL'      },
  { label: 'ETF Internacional',    value: 'ETF_INTERNACIONAL' },
  { label: "Stock / Int'l",        value: 'STOCK'             },
  { label: 'BDRs',                 value: 'BDR'               },
  { label: 'Tesouro Direto',       value: 'TESOURO_DIRETO'    },
  { label: 'Renda Fixa',           value: 'RENDA_FIXA'        },
  { label: 'Cripto',               value: 'CRIPTO'            },
]

function ChartSelect({
  value, onChange, options,
}: {
  value: string | number
  onChange: (v: string) => void
  options: { label: string; value: string | number }[]
}) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      style={{
        padding: '4px 28px 4px 10px',
        height: 30,
        borderRadius: 'var(--radius-md)',
        border: '1px solid oklch(from var(--color-text) l c h / 0.1)',
        background: 'var(--color-surface-2)',
        color: 'var(--color-text)',
        fontSize: 'var(--text-xs)',
        fontWeight: 500,
        cursor: 'pointer',
        outline: 'none',
        appearance: 'none',
        backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%23888'/%3E%3C/svg%3E")`,
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'right 8px center',
        minWidth: 0,
      }}
      onFocus={e => (e.target.style.borderColor = 'var(--color-primary)')}
      onBlur={e  => (e.target.style.borderColor  = 'oklch(from var(--color-text) l c h / 0.1)')}
    >
      {options.map(o => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  )
}

export default function ResumePage() {
  const globalPortfolioId = useAppStore(s => s.selectedPortfolioId)
  const setGlobal         = useAppStore(s => s.setSelectedPortfolioId)

  const [period,          setPeriod]          = useState<PeriodOption>('12m')
  const [assetClass,      setAssetClass]      = useState(ASSET_CLASS_ALL)
  const [showCreateModal, setShowCreateModal] = useState(false)

  const { data: portfolios, isLoading: loadingPortfolios } = usePortfolioList()

  const hasPortfolios = Boolean(portfolios?.length)
  const validGlobalPortfolioId = hasPortfolios && portfolios!.some(p => p.id === globalPortfolioId)
    ? globalPortfolioId
    : null
  const portfolioId: number | null = validGlobalPortfolioId ?? (portfolios?.[0]?.id ?? null)

  useEffect(() => {
    if (loadingPortfolios || !portfolios) return
    if (portfolios.length === 0) return
    if (globalPortfolioId !== portfolioId && portfolioId) {
      setGlobal(portfolioId)
    }
  }, [globalPortfolioId, loadingPortfolios, portfolioId, portfolios, setGlobal])

  const activeAssetType = assetClass === ASSET_CLASS_ALL ? null : assetClass

  const {
    data: summary,
    isLoading: loadingSummary,
    error: summaryError,
  } = usePortfolioSummaryData(portfolioId)
  const { data: positions, isLoading: loadingPositions } = usePositions(portfolioId)
  const { data: classAvailability, isLoading: loadingClassAvailability } = useClassTwrAvailability(portfolioId)

  const selectedClassAvailability = activeAssetType
    ? classAvailability?.find(item => item.asset_type === activeAssetType)
    : null
  const availableClassAssetType = selectedClassAvailability?.available
    ? activeAssetType
    : null

  const { data: monthlyHistory, isLoading: loadingMonthlyHistory } = useMonthlyEvolution(
    activeAssetType ? null : portfolioId,
    period,
  )
  const { data: classMonthlyHistory, isLoading: loadingClassMonthlyHistory } = useClassMonthlyEvolution(
    portfolioId,
    availableClassAssetType,
    period,
  )

  const patrimonioHistory = activeAssetType ? classMonthlyHistory : monthlyHistory
  const classHistoryUnavailable = Boolean(
    activeAssetType
    && !loadingClassAvailability
    && selectedClassAvailability?.available !== true,
  )
  const loadingHistory = activeAssetType
    ? loadingClassAvailability
      || (selectedClassAvailability?.available === true && loadingClassMonthlyHistory)
    : loadingMonthlyHistory
  const historyEmptyMessage = classHistoryUnavailable
    ? selectedClassAvailability?.reason ?? 'Histórico canônico ainda não disponível para esta classe.'
    : 'Sem dados históricos para esta seleção'

  const metrics = summary ? mapPortfolioSummaryMetrics(summary) : null
  const isEstimatedReturn = Boolean(
    metrics?.returnIsEstimated || metrics?.rentabilidadeSource === 'valuation_fallback',
  )
  const loadingKpiCards = loadingPortfolios || loadingSummary
  const summaryContractError = summaryError instanceof Error
    && summaryError.message.startsWith('Contrato summary.v2 inválido:')

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
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
          <EmptyState
            icon={Briefcase}
            title="Você ainda não tem uma carteira"
            description="Crie sua primeira carteira para começar a registrar e acompanhar seus investimentos."
            action={{ label: '+ Criar minha carteira', onClick: () => setShowCreateModal(true) }}
          />
        </div>
        {showCreateModal && <CreatePortfolioModal onClose={() => setShowCreateModal(false)} />}
      </div>
    )
  }

  return (
    <div className="page-container">

      <div className="kpi-grid">
        {loadingKpiCards ? (
          [...Array(4)].map((_, i) => <SkeletonCard key={i} />)
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
              label="Patrimônio Total"
              value={formatBRL(metrics.patrimonio)}
              subValue={formatBRL(metrics.aportado)}
              subLabel="Custo atual das posições abertas"
            />
            <KpiCard
              label="Resultado Total"
              value={formatBRL(metrics.lucroTotal)}
              valueColor={signClass(metrics.lucroTotal)}
              subValue={formatBRL(metrics.variacaoValor)}
              subLabel="Não realizado; total inclui realizado e proventos"
            />
            <KpiCard
              label="Proventos Recebidos (12m)"
              value={formatBRL(metrics.proventos12m)}
              subValue={formatBRL(metrics.proventosTotal)}
              subLabel="Total líquido recebido"
            />
            <KpiCard
              label={isEstimatedReturn ? 'Retorno estimado' : 'Rentabilidade (TWR)'}
              value={`${metrics.rentabilidadePct >= 0 ? '+' : ''}${formatPercent(metrics.rentabilidadePct)}`}
              valueColor={signClass(metrics.rentabilidadePct)}
              subValue={`${metrics.variacaoPct >= 0 ? '+' : ''}${formatPercent(metrics.variacaoPct)}`}
              subLabel="Variação patrimonial das posições abertas"
              bottomLine={isEstimatedReturn ? (
                <span className="text-xs font-semibold" style={{ color: 'var(--color-warning)' }}>
                  Estimativa do valuation atual; TWR indisponível sem snapshot
                </span>
              ) : metrics.rentabilidadeDiariaPct !== null ? (
                <span className={`text-xs font-semibold tabular-nums ${signClass(metrics.rentabilidadeDiariaPct)}`}>
                  {metrics.rentabilidadeDiariaPct >= 0 ? '+' : ''}{formatPercent(metrics.rentabilidadeDiariaPct)} no último fechamento
                </span>
              ) : undefined}
            />
          </>
        ) : (
          <div className="col-span-4 py-8 text-center text-xs" style={{ color: 'var(--color-text-muted)' }}>Nenhum dado disponível. Adicione lançamentos para começar.</div>
        )}
      </div>

      {metrics?.hasPartialPrices && (
        <div
          className="card"
          style={{
            display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem',
            borderColor: 'oklch(from var(--color-warning) l c h / 0.25)',
            background: 'oklch(from var(--color-warning) l c h / 0.08)',
          }}
        >
          <AlertTriangle size={15} style={{ color: 'var(--color-warning)', flexShrink: 0 }} />
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            Alguns ativos ainda não têm cotação atual{metrics.assetsWithoutPrice.length ? `: ${metrics.assetsWithoutPrice.join(', ')}` : ''}. Para eles, o valor investido é usado como referência até a próxima atualização.
          </span>
        </div>
      )}

      <div className="card p-4">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
            <BarChart2 size={14} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
            <span className="section-card-title">Evolução Patrimonial</span>
            {assetClass !== ASSET_CLASS_ALL && (
              <span style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--color-primary)', background: 'oklch(from var(--color-primary) l c h / 0.1)', border: '1px solid oklch(from var(--color-primary) l c h / 0.2)', borderRadius: 'var(--radius-full)', padding: '1px 8px' }}>
                {ASSET_CLASS_OPTIONS.find(o => o.value === assetClass)?.label}
              </span>
            )}
          </div>
          <div className="responsive-actions">
            <ChartSelect value={assetClass} onChange={v => setAssetClass(v)} options={ASSET_CLASS_OPTIONS} />
            <ChartSelect value={period} onChange={v => setPeriod(v as PeriodOption)} options={PERIOD_OPTIONS} />
          </div>
        </div>

        {loadingHistory ? (
          <div className="animate-pulse rounded-lg" style={{ height: 220, background: 'var(--color-surface-offset)' }} />
        ) : patrimonioHistory?.length ? (
          <PatrimonioBarChart data={patrimonioHistory} />
        ) : (
          <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '1rem' }}>
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)' }}>{historyEmptyMessage}</span>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.25rem' }}>
        <TrendingUp size={15} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
        <span style={{ fontSize: 'var(--text-sm)', fontWeight: 700, letterSpacing: '-0.01em', color: 'var(--color-text)' }}>Meus Ativos</span>
        {positions && (
          <span style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text-muted)', background: 'var(--color-surface-offset)', border: '1px solid oklch(from var(--color-text) l c h / 0.07)', borderRadius: 'var(--radius-full)', padding: '1px 8px' }}>
            {positions.reduce((acc, g) => acc + (g.count ?? 0), 0)} ativos
          </span>
        )}
        <div style={{ flex: 1, height: 1, background: 'oklch(from var(--color-text) l c h / 0.07)' }} />
      </div>

      {loadingPositions || !portfolioId ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {[...Array(3)].map((_, i) => <div key={i} className="animate-pulse rounded-xl" style={{ height: 120, background: 'var(--color-surface-offset)' }} />)}
        </div>
      ) : positions && positions.length > 0 ? (
        <PositionTable groups={positions} portfolioId={portfolioId} />
      ) : (
        <div className="card">
          <EmptyState icon={DollarSign} title="Nenhum ativo encontrado" description="Adicione um lançamento para começar a acompanhar sua carteira." />
        </div>
      )}
    </div>
  )
}
