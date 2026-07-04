import { useEffect, useState } from 'react'
import { usePortfolioList } from '@/hooks/usePortfolio'
import type { PortfolioListItem } from '@/hooks/usePortfolio'
import {
  useProventosSummary,
  useProventosDistribuicao,
  useProventosHistoricoMensal,
  useProventosList,
} from '@/hooks/useProventos'
import { formatBRL } from '@/utils/format'
import KpiCard from '@/components/ui/KpiCard'
import ProventosDonutChart from '@/components/charts/ProventosDonutChart'
import ProventosHistoricoTable from '@/components/proventos/ProventosHistoricoTable'
import MeusProventosTable from '@/components/proventos/MeusProventosTable'
import EmptyState from '@/components/ui/EmptyState'
import { DollarSign } from 'lucide-react'

const ASSET_TYPE_OPTIONS = [
  { label: 'Todos os ativos', value: '' },
  { label: 'Acoes', value: 'ACAO' },
  { label: 'FIIs', value: 'FII' },
  { label: 'ETFs Nacionais', value: 'ETF_NACIONAL' },
  { label: 'BDRs', value: 'BDR' },
  { label: 'Stocks', value: 'STOCK' },
  { label: 'ETFs Internacionais', value: 'ETF_INTERNACIONAL' },
]

const PROVENTO_TYPE_OPTIONS = [
  { label: 'Todos os tipos', value: '' },
  { label: 'Dividendos', value: 'DIVIDENDO' },
  { label: 'JCP', value: 'JCP' },
  { label: 'Rendimentos', value: 'RENDIMENTO' },
  { label: 'Amortizacao', value: 'AMORTIZACAO' },
  { label: 'Bonificacao', value: 'BONIFICACAO' },
  { label: 'Subscricao', value: 'SUBSCRICAO' },
  { label: 'Outros', value: 'OUTROS' },
]

const YEARS = [new Date().getFullYear(), new Date().getFullYear() - 1, new Date().getFullYear() - 2]
const PAGE_SIZE = 20

export default function ProventosPage() {
  const { data: portfolios, isLoading: loadingPortfolios } = usePortfolioList()
  const [selectedPortfolio, setSelectedPortfolio] = useState<number | null>(null)
  const portfolioId = selectedPortfolio ?? (portfolios?.[0]?.id ?? 0)

  const [assetTypeFilter, setAssetTypeFilter] = useState('')
  const [dividendTypeFilter, setDividendTypeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [yearFilter, setYearFilter] = useState<number | undefined>(undefined)
  const [page, setPage] = useState(1)

  useEffect(() => {
    setPage(1)
  }, [portfolioId, assetTypeFilter, dividendTypeFilter, statusFilter, yearFilter])

  const { data: summary, isLoading: loadingSummary } = useProventosSummary(portfolioId)
  const { data: distribuicao } = useProventosDistribuicao(portfolioId)
  const hasDistribuicao = (distribuicao?.length ?? 0) > 0

  const { data: historico, isLoading: loadingHistorico } = useProventosHistoricoMensal(
    portfolioId,
    statusFilter || undefined,
    assetTypeFilter || undefined,
    dividendTypeFilter || undefined,
  )
  const { data: lista, isLoading: loadingLista } = useProventosList(portfolioId, {
    status: statusFilter || undefined,
    year: yearFilter,
    asset_type: assetTypeFilter || undefined,
    dividend_type: dividendTypeFilter || undefined,
    page,
    page_size: PAGE_SIZE,
  })

  const totalItems = lista?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE))
  const firstItem = totalItems === 0 ? 0 : (page - 1) * PAGE_SIZE + 1
  const lastItem = Math.min(page * PAGE_SIZE, totalItems)

  if (!loadingPortfolios && !portfolios?.length) {
    return (
      <div className="page-container">
        <EmptyState icon={DollarSign} title="Nenhuma carteira encontrada" description="Crie uma carteira e cadastre ativos para acompanhar proventos." />
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Proventos</h1>
          <p className="page-subtitle">Eventos recebidos e a receber, com Data Com, Data Ex e pagamento.</p>
        </div>
      </div>

      {(portfolios?.length ?? 0) > 1 && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Carteira:</span>
          {(portfolios ?? []).map((p: PortfolioListItem) => (
            <button key={p.id} onClick={() => setSelectedPortfolio(p.id)} className="px-3 py-1 rounded text-xs font-medium transition-colors" style={{ background: portfolioId === p.id ? 'oklch(from var(--color-primary) l c h / 0.15)' : 'var(--color-surface-offset)', color: portfolioId === p.id ? 'var(--color-primary)' : 'var(--color-text-muted)' }}>
              {p.name}
            </button>
          ))}
        </div>
      )}

      <div className="kpi-grid">
        <KpiCard label="Recebido liquido" value={formatBRL(summary?.total_liquido_recebido ?? summary?.total_recebido ?? 0)} subValue={formatBRL(summary?.total_bruto_recebido ?? summary?.total_recebido ?? 0)} subLabel="Bruto recebido" />
        <KpiCard label="A receber liquido" value={formatBRL(summary?.total_liquido_a_receber ?? summary?.total_a_receber ?? 0)} subValue={formatBRL(summary?.total_bruto_a_receber ?? summary?.total_a_receber ?? 0)} subLabel="Bruto a receber" valueColor="text-primary" />
        <KpiCard label="Ultimos 12 meses" value={formatBRL(summary?.total_12m ?? 0)} subLabel="Eventos financeiros" />
        <KpiCard label="Media mensal (12m)" value={formatBRL(summary?.media_mensal_12m ?? 0)} subValue={(summary?.eventos_nao_cash ?? 0).toString()} subLabel="Eventos nao-cash" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {hasDistribuicao && (
          <div className="card p-4">
            <div className="section-card-header"><span className="text-xs font-semibold">Por ativo (12m)</span></div>
            <ProventosDonutChart data={distribuicao!} />
          </div>
        )}

        <div className={`${hasDistribuicao ? 'lg:col-span-3' : 'lg:col-span-4'} flex flex-col gap-4 min-w-0`}>
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1 p-1 rounded-lg" style={{ background: 'var(--color-surface-offset)' }}>
              {[{ label: 'Todos', value: '' }, { label: 'Recebidos', value: 'RECEBIDO' }, { label: 'A receber', value: 'A_RECEBER' }].map(o => (
                <button key={o.value} onClick={() => setStatusFilter(o.value)} className="px-3 py-1 rounded text-xs font-medium transition-colors" style={{ background: statusFilter === o.value ? 'oklch(from var(--color-primary) l c h / 0.15)' : 'transparent', color: statusFilter === o.value ? 'var(--color-primary)' : 'var(--color-text-muted)' }}>{o.label}</button>
              ))}
            </div>
            <select value={assetTypeFilter} onChange={e => setAssetTypeFilter(e.target.value)} className="input text-xs" style={{ width: 'min(220px, 100%)' }}>
              {ASSET_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <select value={dividendTypeFilter} onChange={e => setDividendTypeFilter(e.target.value)} className="input text-xs" style={{ width: 'min(220px, 100%)' }}>
              {PROVENTO_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>

          <div className="card overflow-hidden">
            <div className="section-card-header"><span className="text-xs font-semibold">Historico mensal</span></div>
            <div className="p-4">
              {loadingHistorico || loadingSummary ? <div className="flex flex-col gap-2">{[...Array(4)].map((_, i) => <div key={i} className="h-8 skeleton rounded" />)}</div> : <ProventosHistoricoTable data={historico ?? []} />}
            </div>
          </div>

          <div className="card overflow-hidden">
            <div className="section-card-header flex-wrap gap-2">
              <span className="text-xs font-semibold">Meus proventos</span>
              <div className="flex items-center gap-1 flex-wrap justify-end">
                <button onClick={() => setYearFilter(undefined)} className="px-2 py-0.5 rounded text-xs font-medium transition-colors" style={{ background: yearFilter === undefined ? 'oklch(from var(--color-primary) l c h / 0.15)' : 'transparent', color: yearFilter === undefined ? 'var(--color-primary)' : 'var(--color-text-muted)' }}>Todos</button>
                {YEARS.map(y => <button key={y} onClick={() => setYearFilter(y)} className="px-2 py-0.5 rounded text-xs font-medium transition-colors" style={{ background: yearFilter === y ? 'oklch(from var(--color-primary) l c h / 0.15)' : 'transparent', color: yearFilter === y ? 'var(--color-primary)' : 'var(--color-text-muted)' }}>{y}</button>)}
              </div>
            </div>
            <div className="p-4">
              {loadingLista ? <div className="flex flex-col gap-2">{[...Array(5)].map((_, i) => <div key={i} className="h-10 skeleton rounded" />)}</div> : <MeusProventosTable data={lista?.items ?? []} />}
              {totalItems > 0 && (
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mt-3 text-[10px]" style={{ color: 'var(--color-text-faint)' }}>
                  <span>Exibindo {firstItem}-{lastItem} de {totalItems} eventos</span>
                  <div className="flex items-center gap-2 justify-end">
                    <button disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))} className="px-2 py-1 rounded disabled:opacity-40" style={{ background: 'var(--color-surface-offset)', color: 'var(--color-text-muted)' }}>Anterior</button>
                    <span>Pagina {page} de {totalPages}</span>
                    <button disabled={page >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))} className="px-2 py-1 rounded disabled:opacity-40" style={{ background: 'var(--color-surface-offset)', color: 'var(--color-text-muted)' }}>Proxima</button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
