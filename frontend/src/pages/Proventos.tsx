import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import { useDividends, useDividendSummary } from '@/hooks/useDividends'
import KpiCard from '@/components/dashboard/KpiCard'
import DividendChart from '@/components/dividends/DividendChart'
import DividendTable from '@/components/dividends/DividendTable'
import ModalNovoProvento from '@/components/dividends/ModalNovoProvento'
import { formatBRL } from '@/utils/format'

export default function Proventos() {
  const { portfolioId } = useParams()
  const { selectedPortfolioId } = useAppStore()
  const activeId = portfolioId ? Number(portfolioId) : selectedPortfolioId

  const { data: dividends = [],  isLoading: loadingList    } = useDividends(activeId)
  const { data: summary,         isLoading: loadingSummary } = useDividendSummary(activeId)
  const [showModal, setShowModal] = useState(false)

  if (!activeId) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Selecione uma carteira.</p>
      </div>
    )
  }

  // Calcular yield medio mensal do ano
  const avgMonthly = summary
    ? summary.monthly.reduce((s, m) => s + m.amount, 0) / Math.max(summary.monthly.length, 1)
    : 0

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Proventos</h1>
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            Dividendos, JCP e rendimentos recebidos
          </p>
        </div>
        <button
          className="btn btn-primary flex items-center gap-1.5 text-sm"
          onClick={() => setShowModal(true)}
        >
          <Plus size={15} /> Lançar provento
        </button>
      </div>

      {/* KPIs */}
      {loadingSummary ? (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="kpi-card">
              <div className="skeleton h-3 w-24 mb-2" />
              <div className="skeleton h-7 w-32 mb-1" />
              <div className="skeleton h-3 w-16" />
            </div>
          ))}
        </div>
      ) : summary ? (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          <KpiCard
            label="Total recebido"
            value={formatBRL(summary.total_received)}
            change={`${dividends.length} lançamento${dividends.length !== 1 ? 's' : ''}`}
            positive={null}
          />
          <KpiCard
            label="Média mensal"
            value={formatBRL(avgMonthly)}
            change="Últimos meses"
            positive={null}
          />
          <KpiCard
            label="Projeção próx. 12m"
            value={formatBRL(summary.total_projected)}
            change="Base: histórico recente"
            positive={summary.total_projected > 0}
          />
        </div>
      ) : null}

      {/* Gráfico de barras mensais */}
      <div className="bg-surface border border-[var(--color-border)] rounded-xl p-5">
        <h3 className="text-sm font-semibold mb-4">Proventos por mês</h3>
        {loadingSummary ? (
          <div className="skeleton h-48 w-full rounded-lg" />
        ) : summary && summary.monthly.length > 0 ? (
          <DividendChart data={summary.monthly} />
        ) : (
          <div className="flex items-center justify-center h-40">
            <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
              Nenhum provento registrado ainda.
            </p>
          </div>
        )}
      </div>

      {/* Tabela histórico */}
      <DividendTable dividends={dividends} loading={loadingList} />

      {/* Modal */}
      {showModal && activeId && (
        <ModalNovoProvento
          portfolioId={activeId}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}
