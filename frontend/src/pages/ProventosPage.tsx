import { useEffect, useMemo, useState } from 'react'
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
import { useAppStore } from '@/store/appStore'

const ASSET_TYPE_OPTIONS = [
  { label: 'Todos os ativos', value: '' },
  { label: 'Ações', value: 'ACAO' },
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
  { label: 'Amortização', value: 'AMORTIZACAO' },
  { label: 'Bonificação', value: 'BONIFICACAO' },
  { label: 'Subscrição', value: 'SUBSCRICAO' },
  { label: 'Outros', value: 'OUTROS' },
]

const YEARS = [new Date().getFullYear(), new Date().getFullYear() - 1, new Date().getFullYear() - 2]
const PAGE_SIZE = 20

export default function ProventosPage() {
  const portfolioId = useAppStore(s => s.selectedPortfolioId)

  const [assetTypeFilter, setAssetTypeFilter] = useState('')
  const [dividendTypeFilter, setDividendTypeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [yearFilter, setYearFilter] = useState<number | undefined>(undefined)
  const [page, setPage] = useState(1)

  useEffect(() => {
    setPage(1)
  }, [portfolioId, assetTypeFilter, dividendTypeFilter, statusFilter, yearFilter])

  const proventosFilters = useMemo(() => ({
    status: statusFilter || undefined,
    year: yearFilter,
    asset_type: assetTypeFilter || undefined,
    dividend_type: dividendTypeFilter || undefined,
  }), [assetTypeFilter, dividendTypeFilter, statusFilter, yearFilter])

  const {
    data: summary,
    isLoading: loadingSummary,
    isError: summaryError,
  } = useProventosSummary(portfolioId, proventosFilters)
  const {
    data: distribuicao,
    isLoading: loadingDistribuicao,
    isError: distribuicaoError,
  } = useProventosDistribuicao(
    portfolioId,
    12,
    proventosFilters,
  )
  const hasDistribuicao = (distribuicao?.length ?? 0) > 0

  const {
    data: historico,
    isLoading: loadingHistorico,
    isError: historicoError,
  } =
    useProventosHistoricoMensal(portfolioId, proventosFilters)
  const {
    data: lista,
    isLoading: loadingLista,
    isError: listaError,
  } = useProventosList(portfolioId, {
    ...proventosFilters,
    page,
    page_size: PAGE_SIZE,
  })

  const totalItems = lista?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE))
  const firstItem = totalItems === 0 ? 0 : (page - 1) * PAGE_SIZE + 1
  const lastItem = Math.min(page * PAGE_SIZE, totalItems)

  if (!portfolioId) {
    return (
      <div className="page-container proventos-page">
        <EmptyState
          icon={DollarSign}
          title="Nenhuma carteira selecionada"
          description="Selecione uma carteira no menu superior para acompanhar os proventos."
        />
      </div>
    )
  }

  return (
    <div className="page-container proventos-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Proventos</h1>
          <p className="page-subtitle">Eventos recebidos e a receber, com Data Com, Data Ex e pagamento.</p>
        </div>
      </div>

      <div className="kpi-grid proventos-kpi-grid">
        {loadingSummary && [...Array(4)].map((_, i) => (
          <div key={i} data-testid="proventos-kpi-loading" className="card h-24 skeleton rounded" />
        ))}
        {summaryError && (
          <p role="alert" className="card p-4 text-xs" style={{ color: 'var(--color-danger, var(--color-text-muted))' }}>
            Não foi possível carregar os indicadores de proventos.
          </p>
        )}
        {!loadingSummary && !summaryError && summary && (
          <>
            <KpiCard label="Recebido líquido" value={formatBRL(summary.total_liquido_recebido)} subValue={formatBRL(summary.total_bruto_recebido)} subLabel="Bruto recebido" />
            <KpiCard label="A receber líquido" value={formatBRL(summary.total_liquido_a_receber)} subValue={formatBRL(summary.total_bruto_a_receber)} subLabel="Bruto a receber" valueColor="text-primary" />
            <KpiCard label="Últimos 12 meses" value={formatBRL(summary.total_12m)} subLabel="Eventos financeiros" />
            <KpiCard label="Média mensal (12m)" value={formatBRL(summary.media_mensal_12m)} subValue={summary.eventos_nao_cash.toString()} subLabel="Eventos não monetários" />
          </>
        )}
      </div>

      <div className="proventos-layout has-distribution">
        <div className="card p-4 proventos-distribution-card">
          <div className="section-card-header"><span className="text-xs font-semibold">Por ativo ({yearFilter ?? '12m'})</span></div>
          {loadingDistribuicao && <div data-testid="proventos-distribution-loading" className="h-40 skeleton rounded" />}
          {distribuicaoError && <p role="alert" className="text-xs p-4" style={{ color: 'var(--color-danger, var(--color-text-muted))' }}>Não foi possível carregar a distribuição.</p>}
          {!loadingDistribuicao && !distribuicaoError && hasDistribuicao && <ProventosDonutChart data={distribuicao!} />}
          {!loadingDistribuicao && !distribuicaoError && !hasDistribuicao && <p className="text-xs p-4" style={{ color: 'var(--color-text-muted)' }}>Sem distribuição para os filtros selecionados.</p>}
        </div>

        <div className="proventos-content">
          <div className="filter-bar proventos-filter-bar">
            <div role="group" aria-label="Status do provento" className="flex items-center gap-1 p-1 rounded-lg" style={{ background: 'var(--color-surface-offset)' }}>
              {[{ label: 'Todos', value: '' }, { label: 'Recebidos', value: 'RECEBIDO' }, { label: 'A receber', value: 'A_RECEBER' }].map(o => (
                <button key={o.value} aria-pressed={statusFilter === o.value} onClick={() => setStatusFilter(o.value)} className="px-3 py-1 rounded text-xs font-medium transition-colors" style={{ background: statusFilter === o.value ? 'oklch(from var(--color-primary) l c h / 0.15)' : 'transparent', color: statusFilter === o.value ? 'var(--color-primary)' : 'var(--color-text-muted)' }}>{o.label}</button>
              ))}
            </div>
            <select aria-label="Tipo de ativo" value={assetTypeFilter} onChange={e => setAssetTypeFilter(e.target.value)} className="input text-xs proventos-select">
              {ASSET_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <select aria-label="Tipo de provento" value={dividendTypeFilter} onChange={e => setDividendTypeFilter(e.target.value)} className="input text-xs proventos-select">
              {PROVENTO_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>

          <div className="card overflow-hidden proventos-table-card">
            <div className="section-card-header"><span className="text-xs font-semibold">Historico mensal</span></div>
            <div className="p-4 proventos-table-wrap">
              {loadingHistorico ? <div className="flex flex-col gap-2">{[...Array(4)].map((_, i) => <div key={i} className="h-8 skeleton rounded" />)}</div> : historicoError ? <p role="alert" className="text-xs p-4" style={{ color: 'var(--color-danger, var(--color-text-muted))' }}>Não foi possível carregar o histórico mensal.</p> : <ProventosHistoricoTable data={historico ?? []} />}
            </div>
          </div>

          <div className="card overflow-hidden proventos-table-card">
            <div className="section-card-header flex-wrap gap-2">
              <span className="text-xs font-semibold">Meus proventos</span>
              <div role="group" aria-label="Ano do pagamento" className="flex items-center gap-1 flex-wrap justify-end">
                <button aria-pressed={yearFilter === undefined} onClick={() => setYearFilter(undefined)} className="px-2 py-0.5 rounded text-xs font-medium transition-colors" style={{ background: yearFilter === undefined ? 'oklch(from var(--color-primary) l c h / 0.15)' : 'transparent', color: yearFilter === undefined ? 'var(--color-primary)' : 'var(--color-text-muted)' }}>Todos</button>
                {YEARS.map(y => <button key={y} aria-pressed={yearFilter === y} onClick={() => setYearFilter(y)} className="px-2 py-0.5 rounded text-xs font-medium transition-colors" style={{ background: yearFilter === y ? 'oklch(from var(--color-primary) l c h / 0.15)' : 'transparent', color: yearFilter === y ? 'var(--color-primary)' : 'var(--color-text-muted)' }}>{y}</button>)}
              </div>
            </div>
            <div className="p-4 proventos-table-wrap">
              {loadingLista ? <div className="flex flex-col gap-2">{[...Array(5)].map((_, i) => <div key={i} className="h-10 skeleton rounded" />)}</div> : listaError ? <p role="alert" className="text-xs p-4" style={{ color: 'var(--color-danger, var(--color-text-muted))' }}>Não foi possível carregar os eventos.</p> : <MeusProventosTable data={lista?.items ?? []} />}
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
