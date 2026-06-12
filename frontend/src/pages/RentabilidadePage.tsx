import { useState } from 'react'
import { usePortfolioSummary } from '@/hooks/usePortfolio'
import { useAppStore } from '@/store/appStore'
import { usePortfolioList } from '@/hooks/usePortfolio'
import { formatBRL, formatPercent } from '@/utils/format'
import KpiCard from '@/components/ui/KpiCard'
import clsx from 'clsx'

type Period = '6m' | '12m' | '24m' | 'all'

const PERIODS: { label: string; value: Period }[] = [
  { label: '6M',   value: '6m'  },
  { label: '12M',  value: '12m' },
  { label: '24M',  value: '24m' },
  { label: 'Tudo', value: 'all' },
]

export default function RentabilidadePage() {
  const { selectedPortfolioId } = useAppStore()
  const { data: portfolios = [] } = usePortfolioList()
  const [period, setPeriod] = useState<Period>('12m')

  const { data: summary, isLoading } = usePortfolioSummary(selectedPortfolioId)

  const portfolioName = portfolios.find(p => p.id === selectedPortfolioId)?.name ?? 'Carteira'

  if (!selectedPortfolioId) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Selecione uma carteira na barra superior.</p>
      </div>
    )
  }

  return (
    <div className="p-4 md:p-6 flex flex-col gap-5 max-w-[1400px] mx-auto">
      <div>
        <h1 className="text-xl font-bold">Rentabilidade</h1>
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>{portfolioName} · Evolução e desempenho</p>
      </div>

      {/* Filtro de período */}
      <div
        className="flex items-center gap-1 p-1 rounded-lg self-start"
        style={{ background: 'var(--color-surface-offset)' }}
      >
        {PERIODS.map(p => (
          <button
            key={p.value}
            onClick={() => setPeriod(p.value)}
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

      {/* KPIs */}
      {isLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl skeleton" />
          ))}
        </div>
      ) : summary ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <KpiCard
            label="Total investido"
            value={formatBRL(summary.total_investido ?? 0)}
            subLabel="Capital aportado"
          />
          <KpiCard
            label="Patrimônio atual"
            value={formatBRL(summary.total_patrimonio ?? 0)}
            subLabel={`${formatBRL(summary.lucro_total ?? 0)} de resultado`}
            change={summary.variacao_percentual}
          />
          <KpiCard
            label="Rentabilidade"
            value={formatPercent(summary.rentabilidade_total ?? 0)}
            subLabel={summary.rentabilidade_total >= 0 ? 'Ganho acumulado' : 'Perda acumulada'}
            change={summary.rentabilidade_total}
          />
          <KpiCard
            label="Resultado"
            value={formatBRL(summary.variacao_valor ?? 0)}
            subLabel={formatPercent(summary.variacao_percentual ?? 0)}
            change={summary.variacao_percentual}
          />
        </div>
      ) : (
        <div className="py-12 text-center text-xs" style={{ color: 'var(--color-text-muted)' }}>
          Nenhum dado. Adicione lançamentos para ver a rentabilidade.
        </div>
      )}

      {/* Gráfico placeholder */}
      <div
        className="rounded-xl p-6 flex items-center justify-center h-52"
        style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
      >
        <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Gráfico de evolução histórica — disponível em breve</p>
      </div>
    </div>
  )
}
