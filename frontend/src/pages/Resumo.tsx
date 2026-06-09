import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, RefreshCw } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import { usePortfolioSummary } from '@/hooks/usePerformance'
import { usePortfolios, useCreatePortfolio } from '@/hooks/usePortfolios'
import KpiCard from '@/components/dashboard/KpiCard'
import PositionsTable from '@/components/dashboard/PositionsTable'
import AllocationChart from '@/components/dashboard/AllocationChart'
import ModalNovaCarteira from '@/components/dashboard/ModalNovaCarteira'
import { formatBRL, formatPct } from '@/utils/format'

export default function Resumo() {
  const navigate = useNavigate()
  const { selectedPortfolioId, setSelectedPortfolio } = useAppStore()

  const { data: portfolios = [] } = usePortfolios()
  const { data: summary, isLoading, refetch, isRefetching } = usePortfolioSummary(selectedPortfolioId)
  const createPortfolio = useCreatePortfolio()

  const [showModal, setShowModal] = useState(false)

  async function handleCreatePortfolio(name: string, description: string) {
    const p = await createPortfolio.mutateAsync({ name, description })
    setSelectedPortfolio(p.id)
    navigate('/app/dashboard')
    setShowModal(false)
  }

  // Estado: sem carteiras ainda
  if (!isLoading && portfolios.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5"
          style={{ background: 'oklch(from var(--color-primary) l c h / 0.1)' }}
        >
          <Plus size={28} color="var(--color-primary)" />
        </div>
        <h2 className="text-xl font-semibold mb-2">Nenhuma carteira ainda</h2>
        <p className="text-sm mb-6 max-w-xs" style={{ color: 'var(--color-text-muted)' }}>
          Crie sua primeira carteira para começar a registrar seus investimentos.
        </p>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={16} /> Criar carteira
        </button>
        {showModal && (
          <ModalNovaCarteira
            onClose={() => setShowModal(false)}
            onConfirm={handleCreatePortfolio}
            loading={createPortfolio.isPending}
          />
        )}
      </div>
    )
  }

  // Estado: nenhuma carteira selecionada
  if (!selectedPortfolioId) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
          Selecione uma carteira no menu lateral.
        </p>
      </div>
    )
  }

  // Loading
  if (isLoading) {
    return <ResumoSkeleton />
  }

  const s = summary!
  const gain    = s.total_gain
  const gainPct = s.total_gain_pct
  const dailyPos = s.daily_change >= 0
  const gainPos  = gain >= 0

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Resumo</h1>
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            {portfolios.find(p => p.id === selectedPortfolioId)?.name ?? 'Carteira'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="btn btn-secondary flex items-center gap-1.5 text-sm"
            onClick={() => refetch()}
            disabled={isRefetching}
          >
            <RefreshCw size={15} className={isRefetching ? 'animate-spin' : ''} />
            Atualizar
          </button>
          <button
            className="btn btn-primary flex items-center gap-1.5 text-sm"
            onClick={() => setShowModal(true)}
          >
            <Plus size={15} /> Nova carteira
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard
          label="Patrimônio total"
          value={formatBRL(s.current_value)}
          change={`Investido: ${formatBRL(s.total_invested)}`}
          positive={null}
        />
        <KpiCard
          label="Rentabilidade total"
          value={formatBRL(gain)}
          change={formatPct(gainPct)}
          positive={gainPos}
        />
        <KpiCard
          label="Variação hoje"
          value={formatBRL(s.daily_change)}
          change={formatPct(s.daily_change_pct)}
          positive={dailyPos}
        />
        <KpiCard
          label="Posições abertas"
          value={String(s.positions.length)}
          change={`${s.positions.length} ativo${s.positions.length !== 1 ? 's' : ''}`}
          positive={null}
        />
      </div>

      {/* Gráfico + Tabela */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <PositionsTable positions={s.positions} />
        </div>
        <div>
          <AllocationChart positions={s.positions} />
        </div>
      </div>

      {/* Modal nova carteira */}
      {showModal && (
        <ModalNovaCarteira
          onClose={() => setShowModal(false)}
          onConfirm={handleCreatePortfolio}
          loading={createPortfolio.isPending}
        />
      )}
    </div>
  )
}

function ResumoSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="kpi-card">
            <div className="skeleton h-3 w-24 mb-2" />
            <div className="skeleton h-7 w-32 mb-1" />
            <div className="skeleton h-3 w-16" />
          </div>
        ))}
      </div>
      <div className="skeleton h-64 w-full rounded-xl" />
    </div>
  )
}
