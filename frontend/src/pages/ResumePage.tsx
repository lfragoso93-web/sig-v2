import { useState, useEffect } from 'react'
import { BarChart2, TrendingUp, DollarSign, Activity, Briefcase } from 'lucide-react'
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

// ── Opções dos selects ──
const PERIOD_OPTIONS = [
  { label: 'Últimos 6 meses',  value: 6  },
  { label: 'Últimos 12 meses', value: 12 },
  { label: 'Últimos 24 meses', value: 24 },
  { label: 'Todo período',     value: 60 },
]

const ASSET_CLASS_ALL = 'all'
const ASSET_CLASS_OPTIONS = [
  { label: 'Todas as classes',     value: ASSET_CLASS_ALL },
  { label: 'Ações',               value: 'ACAO'           },
  { label: 'FIIs',                 value: 'FII'            },
  { label: 'ETF Nacional',         value: 'ETF_NACIONAL'   },
  { label: 'ETF Internacional',    value: 'ETF_INTERNACIONAL' },
  { label: 'Stock / Int’l',        value: 'STOCK'          },
  { label: 'Tesouro Direto',       value: 'TESOURO_DIRETO' },
  { label: 'Renda Fixa',           value: 'RENDA_FIXA'     },
  { label: 'Cripto',               value: 'CRIPTO'         },
]

// ── Componente de select reutilizável ──
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
        padding: '4px 8px',
        paddingRight: '24px',
        height: 28,
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
        backgroundPosition: 'right 7px center',
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

// ── Página principal ──
export default function ResumePage() {
  const globalPortfolioId = useAppStore(s => s.selectedPortfolioId)
  const setGlobal         = useAppStore(s => s.setSelectedPortfolioId)

  const [period,          setPeriod]          = useState(12)
  const [assetClass,      setAssetClass]      = useState(ASSET_CLASS_ALL)
  const [showCreateModal, setShowCreateModal] = useState(false)

  const { data: portfolios, isLoading: loadingPortfolios } = usePortfolioList()

  useEffect(() => {
    if (!globalPortfolioId && portfolios && portfolios.length > 0) {
      setGlobal(portfolios[0].id)
    }
  }, [globalPortfolioId, portfolios, setGlobal])

  const portfolioId: number | null = globalPortfolioId ?? (portfolios?.[0]?.id ?? null)

  const activeAssetType = assetClass === ASSET_CLASS_ALL ? null : assetClass

  const { data: summary,           isLoading: loadingSummary    } = usePortfolioSummary(portfolioId)
  const { data: patrimonioHistory, isLoading: loadingHistory     } = usePatrimonioHistory(portfolioId, period, activeAssetType)
  const { data: distribution,      isLoading: loadingDist        } = useAssetDistribution(portfolioId)
  const { data: positions,         isLoading: loadingPositions   } = usePositions(portfolioId)

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

  // ── Loading geral ──
  if (loadingPortfolios) {
    return (
      <div className="page-container">
        <div className="kpi-grid">
          {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      </div>
    )
  }

  // ── Usuário sem carteira ──
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

      {/* ── KPI Cards ── */}
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

      {/* ── Gráficos ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Evolução Patrimonial */}
        <div className="card p-4 lg:col-span-2">

          {/* Header do card — título + dois selects */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '0.5rem',
            marginBottom: '1rem',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <BarChart2 size={14} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
              <span className="section-card-title">Evolução Patrimonial</span>

              {/* Badge mostrando qual classe está filtrada */}
              {assetClass !== ASSET_CLASS_ALL && (
                <span style={{
                  fontSize: '0.68rem', fontWeight: 600,
                  color: 'var(--color-primary)',
                  background: 'oklch(from var(--color-primary) l c h / 0.1)',
                  border: '1px solid oklch(from var(--color-primary) l c h / 0.2)',
                  borderRadius: 'var(--radius-full)',
                  padding: '1px 8px',
                }}>
                  {ASSET_CLASS_OPTIONS.find(o => o.value === assetClass)?.label}
                </span>
              )}
            </div>

            {/* Selects */}
            <div style={{ display: 'flex', gap: 6, flexShrink: 0, flexWrap: 'wrap' }}>
              <ChartSelect
                value={assetClass}
                onChange={v => setAssetClass(v)}
                options={ASSET_CLASS_OPTIONS}
              />
              <ChartSelect
                value={period}
                onChange={v => setPeriod(Number(v))}
                options={PERIOD_OPTIONS}
              />
            </div>
          </div>

          {/* Gráfico */}
          {loadingHistory ? (
            <div
              className="animate-pulse rounded-lg"
              style={{ height: 220, background: 'var(--color-surface-offset)' }}
            />
          ) : patrimonioHistory?.length ? (
            <PatrimonioBarChart
              data={patrimonioHistory}
              singleSeries={assetClass !== ASSET_CLASS_ALL}
            />
          ) : (
            <div
              style={{
                height: 220, display: 'flex',
                alignItems: 'center', justifyContent: 'center',
              }}
            >
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)' }}>
                Sem dados históricos para esta seleção
              </span>
            </div>
          )}
        </div>

        {/* Distribuição */}
        <div className="card p-4">
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: '1rem' }}>
            <Activity size={14} style={{ color: 'var(--color-primary)' }} />
            <span className="section-card-title">Distribuição</span>
          </div>
          {loadingDist ? (
            <div
              className="animate-pulse rounded-lg"
              style={{ height: 220, background: 'var(--color-surface-offset)' }}
            />
          ) : distribution?.length ? (
            <AssetDonutChart data={distribution} />
          ) : (
            <div
              style={{
                height: 220, display: 'flex',
                alignItems: 'center', justifyContent: 'center',
              }}
            >
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)' }}>Sem ativos</span>
            </div>
          )}
        </div>
      </div>

      {/* ── Posições ── */}
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
