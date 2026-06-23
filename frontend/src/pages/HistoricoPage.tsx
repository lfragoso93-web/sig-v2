import { useState } from 'react'
import { TrendingUp, BarChart2, RefreshCw, Wallet, AlertTriangle } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import {
  useDailyEvolution,
  useMonthlyEvolution,
  useEvolutionBackfill,
  type PeriodOption,
} from '@/hooks/useEvolution'
import EvolutionLineChart from '@/components/charts/EvolutionLineChart'
import EvolutionBarChart from '@/components/charts/EvolutionBarChart'
import EmptyState from '@/components/ui/EmptyState'
import KpiCard from '@/components/ui/KpiCard'
import SkeletonCard from '@/components/ui/SkeletonCard'
import { formatBRL, formatPercent, signClass } from '@/utils/format'
import clsx from 'clsx'

const PERIODS: { label: string; value: PeriodOption }[] = [
  { label: '6m',    value: '6m'  },
  { label: '12m',   value: '12m' },
  { label: '24m',   value: '24m' },
  { label: 'Tudo',  value: 'all' },
]

type ViewMode = 'diario' | 'mensal'

export default function HistoricoPage() {
  const portfolioId = useAppStore(s => s.selectedPortfolioId)
  const [period, setPeriod]   = useState<PeriodOption>('12m')
  const [view,   setView]     = useState<ViewMode>('diario')
  const [backfillDone, setBackfillDone] = useState(false)

  const { data: daily,   isLoading: loadingDaily   } = useDailyEvolution(portfolioId, period)
  const { data: monthly, isLoading: loadingMonthly } = useMonthlyEvolution(portfolioId, period)
  const backfill = useEvolutionBackfill(portfolioId)

  if (!portfolioId) {
    return (
      <div className="p-6">
        <EmptyState
          icon={Wallet}
          title="Nenhuma carteira selecionada"
          description="Selecione uma carteira no menu superior para visualizar o historico patrimonial."
        />
      </div>
    )
  }

  // KPIs derivados do ultimo ponto diario
  const last  = daily && daily.length > 0 ? daily[daily.length - 1] : null
  const first = daily && daily.length > 0 ? daily[0] : null
  const variacao = last && first ? last.market_value - first.market_value : null
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
    <div className="page-container">

      {/* Cabecalho */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Historico Patrimonial</h1>
          <p className="page-subtitle">Evolucao do valor de mercado vs. valor investido ao longo do tempo</p>
        </div>
        <button
          onClick={handleBackfill}
          disabled={backfill.isPending}
          className="btn btn-ghost flex items-center gap-2 text-sm"
          title="Recalcular snapshots historicos"
        >
          <RefreshCw size={14} className={clsx(backfill.isPending && 'animate-spin')} />
          {backfillDone ? 'Atualizado!' : 'Atualizar historico'}
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
              label={`Variacao no periodo (${period})`}
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
            Nenhum snapshot encontrado. Clique em "Atualizar historico" para gerar os dados.
          </div>
        )}
      </div>

      {/* Controles: view mode + periodo */}
      <div className="flex flex-wrap items-center justify-between gap-3">
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
              {v === 'diario' ? 'Diario' : 'Mensal'}
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

      {/* Grafico principal */}
      <div className="card overflow-hidden">
        <div className="section-card-header">
          {view === 'diario'
            ? <TrendingUp size={14} style={{ color: 'var(--color-primary)' }} />
            : <BarChart2  size={14} style={{ color: 'var(--color-primary)' }} />}
          <span className="section-card-title">
            {view === 'diario' ? 'Evolucao Diaria' : 'Evolucao Mensal'}
          </span>
        </div>

        <div className="p-4">
          {noData ? (
            <div
              className="flex flex-col items-center gap-3 py-10"
              style={{ color: 'var(--color-text-muted)' }}
            >
              <AlertTriangle size={24} style={{ color: 'var(--color-warning, #f59e0b)' }} />
              <p className="text-sm text-center">
                Nenhum dado historico encontrado.<br />
                Clique em <strong>Atualizar historico</strong> no topo para gerar os snapshots.
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
                  <th className="px-4 py-2 text-left font-medium">Mes</th>
                  <th className="px-4 py-2 text-right font-medium">Valor mercado</th>
                  <th className="px-4 py-2 text-right font-medium">Investido</th>
                  <th className="px-4 py-2 text-right font-medium">P&L nao realiz.</th>
                  <th className="px-4 py-2 text-right font-medium">Rentab.</th>
                </tr>
              </thead>
              <tbody>
                {[...monthly].reverse().map((row, i) => (
                  <tr
                    key={row.period}
                    style={{
                      borderBottom: i < monthly.length - 1 ? '1px solid var(--color-divider)' : 'none',
                      background: i === 0 ? 'var(--color-surface-offset)' : 'transparent',
                    }}
                  >
                    <td className="px-4 py-2.5" style={{ color: 'var(--color-text)' }}>
                      {row.period}
                      {i === 0 && (
                        <span className="ml-2 text-xs px-1 py-0.5 rounded"
                          style={{ background: 'var(--color-primary-highlight)', color: 'var(--color-primary)', fontSize: 10 }}>
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
    </div>
  )
}
