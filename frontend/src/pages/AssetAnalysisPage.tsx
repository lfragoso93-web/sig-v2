import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import api from '@/services/api'
import { formatValue } from './AssetComparisonPage'

type CatalogAsset = { id: number; ticker: string; name: string | null; asset_type: string }
type AssetAnalysis = {
  asset: Record<string, unknown>
  enrichment: Record<string, unknown>
  price_history: Array<Record<string, unknown>>
  dividends: Array<Record<string, unknown>>
  corporate_events: Array<Record<string, unknown>>
  reports: Array<Record<string, unknown>>
}

const sectionLabels: Record<string, string> = {
  stock_fundamentals: 'Fundamentos de ações', fii_indicators: 'Indicadores de FIIs',
  etf_indicators: 'Indicadores de ETFs', bdr_indicators: 'Indicadores de BDRs',
  crypto_indicators: 'Indicadores de criptoativos', treasury_indicators: 'Indicadores do Tesouro',
  international_profile: 'Perfil internacional e consenso', dividend_metrics: 'Métricas de proventos',
  capabilities: 'Cobertura de dados',
}

function DataTable({ title, rows }: { title: string; rows: Array<Record<string, unknown>> }) {
  return <section className="card overflow-hidden">
    <h2 className="border-b px-4 py-3 text-base font-semibold" style={{ borderColor: 'var(--color-border)' }}>{title} ({rows.length})</h2>
    {!rows.length ? <p className="p-4 text-sm" style={{ color: 'var(--color-text-muted)' }}>Sem registros armazenados para este ativo.</p> :
      <div className="overflow-x-auto"><table className="w-full text-left text-xs">
        <thead><tr style={{ color: 'var(--color-text-muted)' }}>{Object.keys(rows[0]).map(key => <th key={key} className="px-3 py-2">{key.split('_').join(' ')}</th>)}</tr></thead>
        <tbody>{rows.map((row, index) => <tr key={index} className="border-t" style={{ borderColor: 'var(--color-border)' }}>{Object.entries(row).map(([key, value]) => <td key={key} className="max-w-xs px-3 py-2">{formatValue(value)}</td>)}</tr>)}</tbody>
      </table></div>}
  </section>
}

export default function AssetAnalysisPage() {
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<CatalogAsset | null>(null)
  const normalized = search.trim()
  const { data: matches = [], isFetching } = useQuery<CatalogAsset[]>({
    queryKey: ['asset-analysis-search', normalized],
    queryFn: () => api.get('/assets/search', { params: { q: normalized, limit: 15 } }).then(response => response.data),
    enabled: normalized.length >= 2, staleTime: 60_000,
  })
  const { data, isLoading, isError } = useQuery<AssetAnalysis>({
    queryKey: ['asset-analysis', selected?.id],
    queryFn: () => api.get('/assets/analysis/' + selected!.id).then(response => response.data),
    enabled: selected !== null, staleTime: 60_000,
  })
  return <div className="page-container space-y-5">
    <header><h1 className="page-title">Análise de ativos</h1><p className="mt-1 text-sm" style={{ color: 'var(--color-text-muted)' }}>Consulte dados do catálogo, fundamentos, preços, proventos e eventos corporativos já disponíveis no sistema.</p></header>
    <section className="card p-4">
      <label htmlFor="asset-analysis-search" className="mb-2 block text-sm font-medium">Buscar ativo por ticker ou nome</label>
      <div className="relative max-w-xl"><Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--color-text-faint)' }} /><input id="asset-analysis-search" className="input w-full pl-9" value={search} onChange={event => { setSearch(event.target.value); setSelected(null) }} placeholder="Ex.: PETR4, HGLG11 ou Bitcoin" autoComplete="off" /></div>
      {normalized.length >= 2 && <div className="mt-2 max-w-xl overflow-hidden rounded-lg border" style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface-2)' }}>
        {isFetching ? <p className="p-3 text-sm">Buscando…</p> : matches.map(asset => <button key={asset.id} type="button" className="block w-full border-b p-3 text-left text-sm last:border-0 hover:bg-black/5" style={{ borderColor: 'var(--color-border)' }} onClick={() => { setSelected(asset); setSearch(asset.ticker + ' — ' + (asset.name ?? asset.asset_type)) }}>{asset.ticker}<span style={{ color: 'var(--color-text-muted)' }}> — {asset.name ?? asset.asset_type}</span></button>)}
        {!isFetching && !matches.length && <p className="p-3 text-sm">Nenhum ativo encontrado no catálogo.</p>}
      </div>}
    </section>
    {isLoading && <p className="text-sm">Carregando dados disponíveis…</p>}
    {isError && <p role="alert" className="text-sm text-red-400">Não foi possível carregar os dados deste ativo.</p>}
    {data && <>
      <section className="card p-4"><h2 className="text-lg font-semibold">{String(data.asset.ticker)}<span className="text-sm font-normal" style={{ color: 'var(--color-text-muted)' }}> {String(data.asset.name ?? '')}</span></h2>
        <p className="mt-1 text-xs" style={{ color: 'var(--color-text-muted)' }}>Classe: {formatValue(data.asset.asset_type)} · Moeda: {formatValue(data.asset.currency)} · Último preço: {formatValue(data.asset.last_price)} · Atualizado: {formatValue(data.asset.last_price_updated_at)} · Cobertura: {formatValue(data.enrichment.coverage_status)}</p>
        <p className="mt-2 text-xs" style={{ color: 'var(--color-text-muted)' }}>Dados informativos, podem ter referências de datas distintas e refletem apenas valores armazenados. Esta página não consulta provedores ao abrir.</p></section>
      <div className="grid gap-4 xl:grid-cols-2">{Object.entries(data.enrichment).filter(([key]) => !['ticker', 'asset_class', 'coverage_status', 'dividend_history'].includes(key)).map(([key, value]) =>
        <section key={key} className="card p-4"><h2 className="mb-3 text-sm font-semibold">{sectionLabels[key] ?? key.split('_').join(' ')}</h2>
          {value && typeof value === 'object' && !Array.isArray(value) ? <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2">{Object.entries(value as Record<string, unknown>).map(([field, fieldValue]) => <div key={field} className="border-b pb-2" style={{ borderColor: 'var(--color-border)' }}><dt className="text-xs capitalize" style={{ color: 'var(--color-text-muted)' }}>{field.split('_').join(' ')}</dt><dd className="mt-1 break-words text-sm">{formatValue(fieldValue)}</dd></div>)}</dl> : <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>{formatValue(value)}</p>}
        </section>)}</div>
      <DataTable title="Histórico de preços (até 90 registros)" rows={data.price_history} />
      <DataTable title="Proventos e eventos monetários (até 100 registros)" rows={data.dividends} />
      <DataTable title="Eventos corporativos (até 100 registros)" rows={data.corporate_events} />
      <section className="card p-4"><h2 className="text-base font-semibold">Relatórios gerenciais</h2><p className="mt-2 text-sm" style={{ color: 'var(--color-text-muted)' }}>{data.reports.length ? 'Relatórios disponíveis para este ativo.' : 'O sistema não possui relatórios gerenciais anexados a este ativo no momento.'}</p></section>
    </>}
  </div>
}
