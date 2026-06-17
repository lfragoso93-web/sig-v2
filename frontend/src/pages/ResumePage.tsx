import { useState, useEffect } from 'react'
import { BarChart2, TrendingUp, DollarSign, Activity, PackageOpen } from 'lucide-react'
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

const PERIOD_OPTIONS = [
  { label: '6M',   value: 6  },
  { label: '12M',  value: 12 },
  { label: '24M',  value: 24 },
  { label: 'Tudo', value: 60 },
]

export default function ResumePage() {
  const globalPortfolioId = useAppStore(s => s.selectedPortfolioId)
  const setGlobal         = useAppStore(s => s.setSelectedPortfolioId)
  const [period, setPeriod] = useState(12)

  const { data: portfolios, isLoading: loadingPortfolios } = usePortfolioList()

  useEffect(() => {
    if (!globalPortfolioId && portfolios && portfolios.length > 0) {
      setGlobal(portfolios[0].id)
    }
  }, [globalPortfolioId, portfolios, setGlobal])

  const portfolioId: number | null = globalPortfolioId ?? (portfolios?.[0]?.id ?? null)

  const { data: summary,           isLoading: loadingSummary  } = usePortfolioSummary(portfolioId)
  const { data: patrimonioHistory, isLoading: loadingHistory   } = usePatrimonioHistory(portfolioId, period)
  const { data: distribution,      isLoading: loadingDist      } = useAssetDistribution(portfolioId)
  const { data: positions,         isLoading: loadingPositions } = usePositions(portfolioId)

  // Valores normalizados — suporta campos EN e PT-BR
  const s = summary as any
  const patrimonio    = s?.total_patrimonio   ?? s?.current_value         ?? 0
  const investido     = s?.total_investido    ?? s?.total_invested        ?? 0
  const lucroTotal    = s?.lucro_total        ?? s?.total_gain            ?? 0
  const ganhoCapital  = s?.ganho_capital      ?? s?.total_gain            ?? 0
  const dividendos12m = s?.dividendos_recebidos_12m ?? 0
  const totalProv     = s?.total_proventos    ?? 0
  const variacaoVal   = s?.variacao_valor     ?? s?.total_gain            ?? 0
  const variacaoPct   = s?.variacao_percentual ?? s?.total_gain_pct       ?? 0
  const rentabilidade = s?.rentabilidade_total ?? s?.total_gain_pct      ?? 0

  // ── Loading inicial (carteiras) ────────────────────────────────────
  if (loadingPortfolios) {
    return (
      <div className="p-4 md:p-6 grid grid-cols-2 md:grid-cols-4 gap-3">
        {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
      </div>
    )
  }

  // ── Sem carteiras ──────────────────────────────────────────────────
  if (!portfolios?.length) {
    return (
      <div className="p-6">
        <EmptyState
          icon={PackageOpen}
          title="Nenhuma carteira encontrada"
          description="Crie sua primeira carteira para começar a registrar seus investimentos."
        />
      </div>
    )
  }

  return (
    <div className="p-4 md:p-6 flex flex-col gap-5 max-w-[1400px] mx-auto">

      {/* ── KPI Cards (4 simétricos) ──────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {loadingSummary ? (
          [...Array(4)].map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            {/* 1 — Patrimônio */}
            <KpiCard
              label="Patrimônio Total"
              value={formatBRL(patrimonio)}
              subValue={formatBRL(investido)}
              subLabel="Valor investido"
              change={variacaoPct}
            />

            {/* 2 — Resultado */}
            <KpiCard
              label="Resultado"
              value={formatBRL(lucroTotal)}
              valueColor={signClass(lucroTotal)}
              subLabel={`Capital ${formatBRL(ganhoCapital)} · Proventos ${formatBRL(totalProv)}`}
              bottomLine={
                <span className={clsx('text-xs font-semibold tabular-nums', signClass(rentabilidade))}>
                  {rentabilidade >= 0 ? '+' : ''}{formatPercent(rentabilidade)} rentabilidade
                </span>
              }
            />

            {/* 3 — Proventos */}
            <KpiCard
              label="Proventos (12m)"
              value={formatBRL(dividendos12m)}
              subValue={formatBRL(totalProv)}
              subLabel="Total acumulado"
            />

            {/* 4 — Variação */}
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

      {/* ── Charts ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Evolução do Patrimônio */}
        <div className="card p-4 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <BarChart2 size={15} style={{ color: 'var(--color-primary)' }} />
              <span className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                Evolução do Patrimônio
              </span>
            </div>
            <div className="flex gap-0.5">
              {PERIOD_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setPeriod(opt.value)}
                  className="px-2.5 py-1 rounded text-xs font-medium transition-colors"
                  style={{
                    background: period === opt.value ? 'oklch(from var(--color-primary) l c h / 0.15)' : 'transparent',
                    color: period === opt.value ? 'var(--color-primary)' : 'var(--color-text-muted)',
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          {loadingHistory ? (
            <div
              className="h-52 animate-pulse rounded-lg"
              style={{ background: 'var(--color-surface-offset)' }}
            />
          ) : patrimonioHistory?.length ? (
            <PatrimonioBarChart data={patrimonioHistory} />
          ) : (
            <div
              className="h-52 flex items-center justify-center text-xs"
              style={{ color: 'var(--color-text-muted)' }}
            >
              Sem dados históricos ainda
            </div>
          )}
        </div>

        {/* Ativos na Carteira */}
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-4">
            <Activity size={15} style={{ color: 'var(--color-primary)' }} />
            <span className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
              Distribuição
            </span>
          </div>
          {loadingDist ? (
            <div
              className="h-52 animate-pulse rounded-lg"
              style={{ background: 'var(--color-surface-offset)' }}
            />
          ) : distribution?.length ? (
            <AssetDonutChart data={distribution} />
          ) : (
            <div
              className="h-52 flex items-center justify-center text-xs"
              style={{ color: 'var(--color-text-muted)' }}
            >
              Sem ativos
            </div>
          )}
        </div>
      </div>

      {/* ── Posições ──────────────────────────────────────────────── */}
      <div className="card overflow-hidden">
        <div
          className="flex items-center gap-2 px-4 py-3"
          style={{ borderBottom: '1px solid var(--color-border)' }}
        >
          <TrendingUp size={15} style={{ color: 'var(--color-primary)' }} />
          <span className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
            Meus Ativos
          </span>
          {positions && (
            <span
              className="ml-1 px-1.5 py-0.5 rounded text-xs tabular-nums"
              style={{
                background: 'var(--color-surface-offset)',
                color: 'var(--color-text-muted)',
              }}
            >
              {positions.reduce((acc, g) => acc + (g.count ?? 0), 0)}
            </span>
          )}
        </div>

        {loadingPositions ? (
          <div className="p-4 flex flex-col gap-2">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="h-10 animate-pulse rounded"
                style={{ background: 'var(--color-surface-offset)' }}
              />
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
