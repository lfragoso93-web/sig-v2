import { useState } from 'react'
import { usePortfolioSummary, usePortfolioList } from '@/hooks/usePortfolio'
import type { PortfolioListItem } from '@/hooks/usePortfolio'
import { useAppStore } from '@/store/appStore'
import { formatBRL, formatPercent } from '@/utils/format'
import KpiCard from '@/components/ui/KpiCard'

type Period = '6m' | '12m' | '24m' | 'all'

const PERIODS: { label: string; value: Period }[] = [
  { label: '6M',   value: '6m'  },
  { label: '12M',  value: '12m' },
  { label: '24M',  value: '24m' },
  { label: 'Tudo', value: 'all' },
]

export default function RentabilidadePage() {
  const { selectedPortfolioId } = useAppStore()
  const { data: portfolios = [] as PortfolioListItem[] } = usePortfolioList()
  const [period, setPeriod] = useState<Period>('12m')

  const { data: summary, isLoading } = usePortfolioSummary(selectedPortfolioId)

  const portfolioName = portfolios.find((p: PortfolioListItem) => p.id === selectedPortfolioId)?.name ?? 'Carteira'

  if (!selectedPortfolioId) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Selecione uma carteira na barra superior.</p>
      </div>
    )
  }

  return (
    <div className="page-container">

      {/* Cabeçalho */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Rentabilidade</h1>
          <p className="page-subtitle">{portfolioName} · Evolução e desempenho</p>
        </div>

        {/* Seletor de período */}
        <div className="flex items-center gap-1 p-1 rounded-lg" style={{ background: 'var(--color-surface-offset)' }}>
          {PERIODS.map((p: { label: string; value: Period }) => (
            <button key={p.value} onClick={() => setPeriod(p.value)}
              className="px-3 py-1 rounded text-xs font-medium transition-colors"
              style={{
                background: period === p.value ? 'oklch(from var(--color-primary) l c h / 0.15)' : 'transparent',
                color: period === p.value ? 'var(--color-primary)' : 'var(--color-text-muted)',
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* KPIs */}
      {isLoading ? (
        <div className="kpi-grid">
          {[...Array(4)].map((_, i) => <div key={i} className="h-24 animate-pulse rounded-xl skeleton" />)}
        </div>
      ) : summary ? (
        <div className="kpi-grid">
          <KpiCard label="Total investido"  value={formatBRL(summary.total_invested  ?? 0)} subLabel="Capital aportado" />
          <KpiCard label="Patrimônio atual" value={formatBRL(summary.current_value   ?? 0)} subLabel={`${formatBRL(summary.total_gain ?? 0)} de resultado`} change={summary.total_gain_pct} />
          <KpiCard label="Rentabilidade"    value={formatPercent(summary.total_gain_pct ?? 0)} subLabel={summary.total_gain_pct >= 0 ? 'Ganho acumulado' : 'Perda acumulada'} change={summary.total_gain_pct} />
          <KpiCard label="Resultado"        value={formatBRL(summary.total_gain ?? 0)} subLabel={formatPercent(summary.total_gain_pct ?? 0)} change={summary.total_gain_pct} />
        </div>
      ) : (
        <div className="py-12 text-center text-xs" style={{ color: 'var(--color-text-muted)' }}>Nenhum dado. Adicione lançamentos para ver a rentabilidade.</div>
      )}

      {/* Gráfico histórico (em breve) */}
      <div className="card p-6 flex items-center justify-center h-52">
        <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Gráfico de evolução histórica — disponível em breve</p>
      </div>
    </div>
  )
}
