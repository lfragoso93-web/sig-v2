import { useState, useEffect } from 'react'
import { BarChart2, TrendingUp, DollarSign, Activity, Briefcase, Target } from 'lucide-react'
import clsx from 'clsx'
import {
  usePortfolioList,
  usePatrimonioHistory,
  useAssetDistribution,
  usePositions,
} from '@/hooks/usePortfolio'
import { useRentabilidadeKpis } from '@/hooks/useRentabilidade'
import { useClassTargets } from '@/hooks/useClassTargets'
import type { ClassTargetRow } from '@/hooks/useClassTargets'
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
  { label: 'Últimos 6 meses',  value: 6  },
  { label: 'Últimos 12 meses', value: 12 },
  { label: 'Últimos 24 meses', value: 24 },
  { label: 'Todo período',     value: 60 },
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

// ---------------------------------------------------------------------------
// AllocationTargetWidget — Sprint 5E
// ---------------------------------------------------------------------------
function AllocationTargetWidget({ rows }: { rows: ClassTargetRow[] }) {
  const [collapsed, setCollapsed] = useState(false)

  // So exibe se ao menos uma classe tem alvo configurado
  const hasAnyTarget = rows.some(r => r.target_pct > 0)
  if (!hasAnyTarget) {
    return (
      <div style={{
        marginTop: '0.75rem',
        padding: '10px 12px',
        borderRadius: 'var(--radius-md)',
        background: 'var(--color-surface-offset)',
        border: '1px dashed oklch(from var(--color-text) l c h / 0.1)',
        textAlign: 'center',
      }}>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)' }}>
          Configure metas em{' '}
          <a href="/carteira/metas" style={{ color: 'var(--color-primary)', textDecoration: 'underline' }}>
            Configurações → Metas
          </a>
        </span>
      </div>
    )
  }

  return (
    <div style={{ marginTop: '0.75rem' }}>
      {/* Header colapsavel */}
      <button
        onClick={() => setCollapsed(c => !c)}
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          width: '100%', background: 'none', border: 'none',
          cursor: 'pointer', padding: '2px 0', marginBottom: collapsed ? 0 : '0.5rem',
        }}
      >
        <Target size={12} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
        <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text)' }}>
          Alvo da Carteira
        </span>
        <span style={{
          marginLeft: 'auto',
          fontSize: '0.6rem',
          color: 'var(--color-text-faint)',
          transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)',
          transition: 'transform 0.15s',
        }}>▼</span>
      </button>

      {!collapsed && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
          {rows.map(row => {
            const delta = row.delta_pct
            // Verde: dentro de ±2pp | Amarelo: sub | Vermelho: sobre
            const statusColor =
              Math.abs(delta) <= 2
                ? 'var(--color-success)'
                : delta > 0
                  ? 'var(--color-error)'
                  : 'var(--color-warning)'

            const barMax = Math.max(row.current_pct, row.target_pct, 1)
            const currentW = Math.min((row.current_pct / barMax) * 100, 100)
            const targetW  = Math.min((row.target_pct  / barMax) * 100, 100)

            return (
              <div key={row.asset_type}>
                {/* Label + delta */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 3 }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', fontWeight: 500 }}>
                    {row.label}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontSize: '0.68rem', color: 'var(--color-text-faint)' }}>
                      {row.current_pct.toFixed(1)}% <span style={{ color: 'var(--color-text-faint)', fontWeight: 400 }}>/ alvo {row.target_pct.toFixed(1)}%</span>
                    </span>
                    {row.target_pct > 0 && (
                      <span style={{
                        fontSize: '0.62rem', fontWeight: 700,
                        color: statusColor,
                        minWidth: 36, textAlign: 'right',
                      }}>
                        {delta > 0 ? '+' : ''}{delta.toFixed(1)}pp
                      </span>
                    )}
                  </div>
                </div>

                {/* Barra de progresso */}
                <div style={{
                  position: 'relative',
                  height: 6,
                  borderRadius: 'var(--radius-full)',
                  background: 'var(--color-surface-offset)',
                  overflow: 'visible',
                }}>
                  {/* Barra atual */}
                  <div style={{
                    position: 'absolute', top: 0, left: 0,
                    height: '100%',
                    width: `${currentW}%`,
                    background: row.color,
                    borderRadius: 'var(--radius-full)',
                    opacity: 0.85,
                    transition: 'width 0.4s ease',
                  }} />
                  {/* Marcador de alvo (linha tracejada vertical) */}
                  {row.target_pct > 0 && (
                    <div style={{
                      position: 'absolute',
                      top: -3, bottom: -3,
                      left: `${targetW}%`,
                      width: 2,
                      background: 'var(--color-text-muted)',
                      borderRadius: 1,
                      opacity: 0.55,
                      transform: 'translateX(-50%)',
                    }} />
                  )}
                </div>
              </div>
            )
          })}

          {/* Legenda compacta */}
          <div style={{ display: 'flex', gap: 10, marginTop: 4, flexWrap: 'wrap' }}>
            {[
              { color: 'var(--color-success)', label: '±2pp do alvo' },
              { color: 'var(--color-warning)', label: 'Subalocado' },
              { color: 'var(--color-error)',   label: 'Sobrealocado' },
            ].map(leg => (
              <div key={leg.label} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <div style={{ width: 8, height: 8, borderRadius: 2, background: leg.color, flexShrink: 0 }} />
                <span style={{ fontSize: '0.6rem', color: 'var(--color-text-faint)' }}>{leg.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// ResumePage
// ---------------------------------------------------------------------------
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

  const { data: kpis,              isLoading: loadingKpis      } = useRentabilidadeKpis(portfolioId)
  const { data: patrimonioHistory, isLoading: loadingHistory   } = usePatrimonioHistory(portfolioId, period, activeAssetType)
  const { data: distribution,      isLoading: loadingDist      } = useAssetDistribution(portfolioId)
  const { data: positions,         isLoading: loadingPositions } = usePositions(portfolioId)
  const { data: classTargets,      isLoading: loadingTargets   } = useClassTargets(portfolioId)

  const patrimonio     = kpis?.patrimonio_atual        ?? 0
  const aportado       = kpis?.total_aportado          ?? 0
  const totalPnl       = kpis?.total_pnl               ?? 0
  const ganhoNaoReal   = kpis?.ganho_nao_realizado      ?? 0
  const ganhoReal      = kpis?.ganho_realizado          ?? 0
  const proventos12m   = kpis?.proventos_12m            ?? 0
  const proventosTotal = kpis?.proventos_total          ?? 0
  const retornoTotal   = kpis?.retorno_total_pct        ?? 0
  const retornoMes     = kpis?.retorno_mes_pct          ?? 0
  const retorno12m     = kpis?.retorno_12m_pct          ?? 0
  const retornoInicio  = kpis?.retorno_desde_inicio_pct ?? 0

  const loadingKpiCards = loadingPortfolios || loadingKpis

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

      {/* ── KPI Cards ── */}
      <div className="kpi-grid">
        {loadingKpiCards ? (
          [...Array(4)].map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            {/* Patrimônio Total */}
            <KpiCard
              label="Patrimônio Total"
              value={formatBRL(patrimonio)}
              subValue={formatBRL(aportado)}
              subLabel="Total aportado"
              change={retornoTotal}
            />

            {/* Resultado Total */}
            <KpiCard
              label="Resultado Total"
              value={formatBRL(totalPnl)}
              valueColor={signClass(totalPnl)}
              subLabel={`Não realizado ${formatBRL(ganhoNaoReal)} · Realizado ${formatBRL(ganhoReal)}`}
              bottomLine={
                <span
                  title="Retorno total = (PnL + proventos) / total aportado"
                  className={clsx('text-xs font-semibold tabular-nums', signClass(retornoTotal))}
                  style={{ cursor: 'help' }}
                >
                  {retornoTotal >= 0 ? '+' : ''}{formatPercent(retornoTotal)} retorno total
                </span>
              }
            />

            {/* Proventos */}
            <KpiCard
              label="Proventos (12m)"
              value={formatBRL(proventos12m)}
              subValue={formatBRL(proventosTotal)}
              subLabel="Total acumulado"
            />

            {/* Rentabilidade */}
            <KpiCard
              label="Rentabilidade"
              value={
                <span className={clsx('tabular-nums', signClass(retornoInicio))}>
                  {retornoInicio >= 0 ? '+' : ''}{formatPercent(retornoInicio)}
                </span>
              }
              subLabel="Desde o início"
              bottomLine={
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                  Mês:&nbsp;
                  <span className={clsx('font-semibold tabular-nums', signClass(retornoMes))}>
                    {retornoMes >= 0 ? '+' : ''}{formatPercent(retornoMes)}
                  </span>
                  &nbsp;·&nbsp;12m:&nbsp;
                  <span className={clsx('font-semibold tabular-nums', signClass(retorno12m))}>
                    {retorno12m >= 0 ? '+' : ''}{formatPercent(retorno12m)}
                  </span>
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
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <BarChart2 size={14} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
              <span className="section-card-title">Evolução Patrimonial</span>
              {assetClass !== ASSET_CLASS_ALL && (
                <span style={{
                  fontSize: '0.68rem', fontWeight: 600,
                  color: 'var(--color-primary)',
                  background: 'oklch(from var(--color-primary) l c h / 0.1)',
                  border: '1px solid oklch(from var(--color-primary) l c h / 0.2)',
                  borderRadius: 'var(--radius-full)', padding: '1px 8px',
                }}>
                  {ASSET_CLASS_OPTIONS.find(o => o.value === assetClass)?.label}
                </span>
              )}
            </div>
            <div style={{ display: 'flex', gap: 6, flexShrink: 0, flexWrap: 'wrap' }}>
              <ChartSelect value={assetClass} onChange={v => setAssetClass(v)} options={ASSET_CLASS_OPTIONS} />
              <ChartSelect value={period} onChange={v => setPeriod(Number(v))} options={PERIOD_OPTIONS} />
            </div>
          </div>

          {loadingHistory ? (
            <div className="animate-pulse rounded-lg" style={{ height: 220, background: 'var(--color-surface-offset)' }} />
          ) : patrimonioHistory?.length ? (
            <PatrimonioBarChart data={patrimonioHistory} singleSeries={assetClass !== ASSET_CLASS_ALL} />
          ) : (
            <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)' }}>Sem dados históricos para esta seleção</span>
            </div>
          )}
        </div>

        {/* Distribuição + Alvo */}
        <div className="card p-4">
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: '1rem' }}>
            <Activity size={14} style={{ color: 'var(--color-primary)' }} />
            <span className="section-card-title">Distribuição</span>
          </div>

          {/* Donut */}
          {loadingDist ? (
            <div className="animate-pulse rounded-lg" style={{ height: 180, background: 'var(--color-surface-offset)' }} />
          ) : distribution?.length ? (
            <AssetDonutChart data={distribution} />
          ) : (
            <div style={{ height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)' }}>Sem ativos</span>
            </div>
          )}

          {/* Widget de alvo — Sprint 5E */}
          {!loadingTargets && classTargets && classTargets.length > 0 && (
            <AllocationTargetWidget rows={classTargets} />
          )}
          {loadingTargets && (
            <div className="animate-pulse rounded-md" style={{ height: 80, background: 'var(--color-surface-offset)', marginTop: '0.75rem' }} />
          )}
        </div>
      </div>

      {/* ── Meus Ativos ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '0.75rem',
        marginTop: '0.25rem',
      }}>
        <TrendingUp size={15} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
        <span style={{
          fontSize: 'var(--text-sm)', fontWeight: 700,
          letterSpacing: '-0.01em', color: 'var(--color-text)',
        }}>Meus Ativos</span>
        {positions && (
          <span style={{
            fontSize: 'var(--text-xs)', fontWeight: 500,
            color: 'var(--color-text-muted)',
            background: 'var(--color-surface-offset)',
            border: '1px solid oklch(from var(--color-text) l c h / 0.07)',
            borderRadius: 'var(--radius-full)',
            padding: '1px 8px',
          }}>
            {positions.reduce((acc, g) => acc + (g.count ?? 0), 0)} ativos
          </span>
        )}
        <div style={{ flex: 1, height: 1, background: 'oklch(from var(--color-text) l c h / 0.07)' }} />
      </div>

      {/* ── Tabela de posições ── */}
      {loadingPositions || !portfolioId ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {[...Array(3)].map((_, i) => (
            <div key={i} className="animate-pulse rounded-xl" style={{ height: 120, background: 'var(--color-surface-offset)' }} />
          ))}
        </div>
      ) : positions && positions.length > 0 ? (
        <PositionTable groups={positions} portfolioId={portfolioId} />
      ) : (
        <div className="card">
          <EmptyState
            icon={DollarSign}
            title="Nenhum ativo encontrado"
            description="Adicione um lançamento para começar a acompanhar sua carteira."
          />
        </div>
      )}
    </div>
  )
}
