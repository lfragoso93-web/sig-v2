import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { TrendingUp, TrendingDown, DollarSign, BarChart2, Globe, RefreshCw } from 'lucide-react'
import clsx from 'clsx'
import {
  AreaChart, Area, BarChart, Bar,
  PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { usePortfolioPerformance } from '@/hooks/usePerformance'
import { formatBRL, formatUSD, formatPercent, formatQuantity, signClass } from '@/utils/format'
import { ASSET_TYPE_LABELS, ASSET_TYPE_COLORS } from '@/utils/assetTypes'

// ─── KPI Card ─────────────────────────────────────────────────────────────────

function KpiCard({
  label, value, sub, positive,
}: { label: string; value: string; sub?: string; positive?: boolean }) {
  return (
    <div className="card p-4">
      <p className="text-xs text-muted mb-1">{label}</p>
      <p className={clsx('text-xl font-bold tabular-nums', positive === undefined ? 'text-gray-900 dark:text-gray-100' : positive ? 'text-positive' : 'text-negative')}>
        {value}
      </p>
      {sub && <p className="text-xs text-muted mt-0.5">{sub}</p>}
    </div>
  )
}

// ─── Badge retorno ────────────────────────────────────────────────────────────

function ReturnBadge({ pct }: { pct: number }) {
  const pos = pct >= 0
  return (
    <span className={clsx(
      'inline-flex items-center gap-0.5 text-xs font-semibold px-1.5 py-0.5 rounded tabular-nums',
      pos ? 'bg-positive/10 text-positive' : 'bg-negative/10 text-negative'
    )}>
      {pos ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
      {formatPercent(pct)}
    </span>
  )
}

// ─── Tooltip customizado ──────────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="card p-3 text-xs shadow-lg min-w-[160px]">
      <p className="font-medium mb-2">{label}</p>
      {payload.map((p: any) => (
        <div key={p.name} className="flex justify-between gap-4">
          <span className="text-muted">{p.name}</span>
          <span className="font-medium tabular-nums">{formatBRL(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

// ─── Página principal ─────────────────────────────────────────────────────────

const TABS = ['Visão Geral', 'Ativos', 'Por Tipo', 'Evolução'] as const
type Tab = typeof TABS[number]

export default function Rentabilidade() {
  const { portfolioId } = useParams<{ portfolioId: string }>()
  const id = Number(portfolioId)
  const { data: perf, isLoading, error, refetch, isFetching } = usePortfolioPerformance(id)
  const [tab, setTab] = useState<Tab>('Visão Geral')
  const [sortBy, setSortBy] = useState<'return_pct' | 'current_value' | 'unrealized_pnl'>('current_value')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  if (isLoading) return <PerformanceSkeleton />
  if (error || !perf) return (
    <div className="empty-state">
      <BarChart2 size={40} className="text-muted mb-3" />
      <h3>Dados indisponíveis</h3>
      <p>Não foi possível carregar a rentabilidade. Tente novamente.</p>
      <button className="btn-primary mt-4" onClick={() => refetch()}>Tentar novamente</button>
    </div>
  )

  const sorted = [...perf.assets].sort((a, b) => {
    const mul = sortDir === 'desc' ? -1 : 1
    return mul * (a[sortBy] - b[sortBy])
  })

  const isPositive = perf.return_pct >= 0

  // ─── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col gap-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">{perf.portfolio_name}</h1>
          <p className="text-sm text-muted">Rentabilidade da carteira</p>
        </div>
        <button
          onClick={() => refetch()}
          className="btn-icon" aria-label="Atualizar"
        >
          <RefreshCw size={16} className={clsx(isFetching && 'animate-spin')} />
        </button>
      </div>

      {/* KPIs principais */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard
          label="Valor Atual"
          value={formatBRL(perf.total_current)}
          sub={`Investido: ${formatBRL(perf.total_cost)}`}
        />
        <KpiCard
          label="Retorno Total"
          value={formatBRL(perf.total_pnl)}
          sub={formatPercent(perf.return_pct)}
          positive={isPositive}
        />
        <KpiCard
          label="Ganho Não Realizado"
          value={formatBRL(perf.total_unrealized)}
          positive={perf.total_unrealized >= 0}
        />
        <KpiCard
          label="Ganho Realizado"
          value={formatBRL(perf.total_realized)}
          positive={perf.total_realized >= 0}
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-light-border dark:border-dark-border">
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={clsx(
              'px-4 py-2 text-sm font-medium -mb-px border-b-2 transition-colors',
              tab === t
                ? 'border-brand-primary text-brand-primary'
                : 'border-transparent text-muted hover:text-gray-700 dark:hover:text-gray-300'
            )}
          >{t}</button>
        ))}
      </div>

      {/* ── TAB: Visão Geral ──────────────────────────────────────────────── */}
      {tab === 'Visão Geral' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Donut alocação */}
          <div className="card p-4">
            <h3 className="text-sm font-semibold mb-4">Alocação por Tipo</h3>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={perf.by_type}
                  dataKey="current"
                  nameKey="asset_type"
                  cx="50%" cy="50%"
                  innerRadius={60} outerRadius={90}
                  paddingAngle={2}
                >
                  {perf.by_type.map((entry) => (
                    <Cell
                      key={entry.asset_type}
                      fill={ASSET_TYPE_COLORS[entry.asset_type] ?? '#94a3b8'}
                    />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(v: number) => formatBRL(v)}
                  labelFormatter={(l) => ASSET_TYPE_LABELS[l] ?? l}
                />
                <Legend
                  formatter={(v) => ASSET_TYPE_LABELS[v] ?? v}
                  iconType="circle" iconSize={8}
                  wrapperStyle={{ fontSize: 12 }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Rentabilidade por tipo */}
          <div className="card p-4">
            <h3 className="text-sm font-semibold mb-4">Retorno por Tipo (%)</h3>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={perf.by_type} layout="vertical" margin={{ left: 16 }}>
                <XAxis type="number" tickFormatter={(v) => `${v.toFixed(1)}%`} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="asset_type" tickFormatter={(v) => ASSET_TYPE_LABELS[v] ?? v} width={110} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => `${v.toFixed(2)}%`} />
                <Bar dataKey="return_pct" name="Retorno %" radius={[0, 4, 4, 0]}>
                  {perf.by_type.map((entry) => (
                    <Cell
                      key={entry.asset_type}
                      fill={entry.return_pct >= 0 ? 'var(--color-positive)' : 'var(--color-negative)'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* ── TAB: Ativos ───────────────────────────────────────────────────── */}
      {tab === 'Ativos' && (
        <div className="card overflow-hidden">
          {/* Controles sort */}
          <div className="flex gap-2 p-3 border-b border-light-border dark:border-dark-border flex-wrap">
            <span className="text-xs text-muted self-center">Ordenar por:</span>
            {(['current_value', 'return_pct', 'unrealized_pnl'] as const).map(k => (
              <button
                key={k}
                onClick={() => {
                  if (sortBy === k) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
                  else { setSortBy(k); setSortDir('desc') }
                }}
                className={clsx(
                  'px-2.5 py-1 text-xs rounded transition-colors',
                  sortBy === k
                    ? 'bg-brand-primary/10 text-brand-primary font-medium'
                    : 'text-muted hover:text-gray-700'
                )}
              >
                {{ current_value: 'Valor', return_pct: 'Retorno %', unrealized_pnl: 'Ganho/Perda' }[k]}
                {sortBy === k && (sortDir === 'desc' ? ' ↓' : ' ↑')}
              </button>
            ))}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-light-border dark:border-dark-border">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-muted">Ativo</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-muted">Qtd</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-muted">P. Médio</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-muted">P. Atual</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-muted">Custo</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-muted">Valor Atual</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-muted">Ganho/Perda</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-muted">Retorno</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-muted">% Cart.</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-light-border dark:divide-dark-border">
                {sorted.map(a => (
                  <tr key={a.ticker} className="hover:bg-surface-2 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-xs">{a.ticker}</span>
                        {a.currency === 'USD' && (
                          <span className="flex items-center gap-0.5 text-xs bg-blue/10 text-blue px-1.5 rounded">
                            <Globe size={9} /> USD
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-muted">{ASSET_TYPE_LABELS[a.asset_type] ?? a.asset_type}</span>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-xs">{formatQuantity(a.quantity)}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-xs">
                      {a.currency === 'USD'
                        ? <><div>{formatUSD(a.avg_price)}</div><div className="text-muted">{formatBRL(a.avg_price_brl)}</div></>
                        : formatBRL(a.avg_price_brl)
                      }
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-xs">
                      {a.currency === 'USD'
                        ? <><div>{formatUSD(a.current_price)}</div><div className="text-muted">{formatBRL(a.current_price_brl)}</div></>
                        : formatBRL(a.current_price_brl)
                      }
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-xs">{formatBRL(a.cost_basis)}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-xs font-medium">{formatBRL(a.current_value)}</td>
                    <td className={clsx('px-4 py-3 text-right tabular-nums text-xs font-medium', signClass(a.total_pnl))}>
                      {formatBRL(a.total_pnl)}
                      {a.fx_variation_pct !== null && (
                        <div className="text-xs text-muted font-normal">
                          câmbio {formatPercent(a.fx_variation_pct!)}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <ReturnBadge pct={a.return_pct} />
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-xs text-muted">
                      {a.allocation_pct.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── TAB: Por Tipo ─────────────────────────────────────────────────── */}
      {tab === 'Por Tipo' && (
        <div className="grid gap-3">
          {perf.by_type
            .sort((a, b) => b.current - a.current)
            .map(t => (
              <div key={t.asset_type} className="card p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-3 h-3 rounded-full"
                      style={{ background: ASSET_TYPE_COLORS[t.asset_type] ?? '#94a3b8' }}
                    />
                    <span className="font-semibold text-sm">{ASSET_TYPE_LABELS[t.asset_type] ?? t.asset_type}</span>
                    <span className="text-xs text-muted">{t.count} ativo{t.count > 1 ? 's' : ''}</span>
                  </div>
                  <ReturnBadge pct={t.return_pct} />
                </div>
                <div className="grid grid-cols-3 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-muted">Custo</p>
                    <p className="font-medium tabular-nums">{formatBRL(t.cost)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted">Valor Atual</p>
                    <p className="font-medium tabular-nums">{formatBRL(t.current)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted">Ganho/Perda</p>
                    <p className={clsx('font-medium tabular-nums', signClass(t.pnl))}>{formatBRL(t.pnl)}</p>
                  </div>
                </div>
                {/* barra de alocacao */}
                <div className="mt-3">
                  <div className="flex justify-between text-xs text-muted mb-1">
                    <span>Alocação</span>
                    <span>{t.allocation_pct.toFixed(1)}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-surface-offset overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${Math.min(t.allocation_pct, 100)}%`,
                        background: ASSET_TYPE_COLORS[t.asset_type] ?? '#94a3b8',
                      }}
                    />
                  </div>
                </div>
              </div>
            ))}
        </div>
      )}

      {/* ── TAB: Evolução ─────────────────────────────────────────────────── */}
      {tab === 'Evolução' && (
        <div className="card p-4">
          <h3 className="text-sm font-semibold mb-4">Evolução do Patrimônio Investido</h3>
          {perf.history.length === 0 ? (
            <p className="text-sm text-muted text-center py-8">Nenhuma transação registrada ainda.</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={perf.history} margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
                <defs>
                  <linearGradient id="gradInvested" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="var(--color-brand-primary)" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="var(--color-brand-primary)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={(v) => formatBRL(v, true)} tick={{ fontSize: 11 }} width={72} />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="net_invested"
                  name="Total Investido"
                  stroke="var(--color-brand-primary)"
                  fill="url(#gradInvested)"
                  strokeWidth={2}
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      )}

    </div>
  )
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function PerformanceSkeleton() {
  return (
    <div className="flex flex-col gap-6 animate-pulse">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="card p-4">
            <div className="skeleton skeleton-text w-24 mb-2" />
            <div className="skeleton skeleton-text w-32" />
          </div>
        ))}
      </div>
      <div className="skeleton h-10 rounded-lg" />
      <div className="card p-4">
        <div className="skeleton h-60 rounded-lg" />
      </div>
    </div>
  )
}
