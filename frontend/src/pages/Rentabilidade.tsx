import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { usePortfolioSummary, useEquityHistory } from '@/hooks/usePerformance'
import { useAppStore } from '@/store/appStore'
import KpiCard from '@/components/dashboard/KpiCard'
import EquityChart from '@/components/performance/EquityChart'
import PerformanceTable from '@/components/performance/PerformanceTable'
import { formatBRL, formatPct } from '@/utils/format'

type Period = '1m' | '3m' | '6m' | '1y' | 'all'

const PERIODS: { label: string; value: Period }[] = [
  { label: '1M',   value: '1m'  },
  { label: '3M',   value: '3m'  },
  { label: '6M',   value: '6m'  },
  { label: '1 ano',value: '1y'  },
  { label: 'Tudo', value: 'all' },
]

export default function Rentabilidade() {
  const { portfolioId } = useParams()
  const { selectedPortfolioId } = useAppStore()
  const activeId = portfolioId ? Number(portfolioId) : selectedPortfolioId

  const [period, setPeriod] = useState<Period>('1y')

  const { data: summary, isLoading: loadingSummary } = usePortfolioSummary(activeId)
  const { data: equity,  isLoading: loadingEquity  } = useEquityHistory(activeId, period)

  if (!activeId) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Selecione uma carteira.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold">Rentabilidade</h1>
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
          Evolução e desempenho da carteira
        </p>
      </div>

      {/* KPIs de performance */}
      {loadingSummary ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="kpi-card">
              <div className="skeleton h-3 w-20 mb-2" />
              <div className="skeleton h-7 w-28 mb-1" />
              <div className="skeleton h-3 w-14" />
            </div>
          ))}
        </div>
      ) : summary ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <KpiCard
            label="Total investido"
            value={formatBRL(summary.total_invested)}
            change="Capital aportado"
            positive={null}
          />
          <KpiCard
            label="Valor atual"
            value={formatBRL(summary.current_value)}
            change={`${formatBRL(summary.total_gain)} de ganho`}
            positive={summary.total_gain >= 0}
          />
          <KpiCard
            label="Rentab. total"
            value={formatPct(summary.total_gain_pct)}
            change={summary.total_gain >= 0 ? 'Ganho realiz. + não realiz.' : 'Perda acumulada'}
            positive={summary.total_gain_pct >= 0}
          />
          <KpiCard
            label="No dia"
            value={formatPct(summary.daily_change_pct)}
            change={formatBRL(summary.daily_change)}
            positive={summary.daily_change >= 0}
          />
        </div>
      ) : null}

      {/* Gráfico de evolução */}
      <div className="bg-surface border border-[var(--color-border)] rounded-xl p-5">
        {/* Seletor de período */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold">Evolução do patrimônio</h3>
          <div className="flex items-center gap-1 p-1 rounded-lg" style={{ background: 'var(--color-surface-offset)' }}>
            {PERIODS.map(p => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                className="px-3 py-1 rounded text-xs font-medium transition-colors"
                style={{
                  background: period === p.value ? 'var(--color-surface)' : 'transparent',
                  color: period === p.value ? 'var(--color-text)' : 'var(--color-text-muted)',
                  boxShadow: period === p.value ? 'var(--shadow-sm)' : 'none',
                }}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {loadingEquity ? (
          <div className="skeleton h-56 w-full rounded-lg" />
        ) : equity && equity.length > 0 ? (
          <EquityChart data={equity} />
        ) : (
          <div className="flex items-center justify-center h-48">
            <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
              Sem dados para o período selecionado.
            </p>
          </div>
        )}
      </div>

      {/* Tabela de performance por ativo */}
      {!loadingSummary && summary && (
        <PerformanceTable positions={summary.positions} />
      )}
    </div>
  )
}
