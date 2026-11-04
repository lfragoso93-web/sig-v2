import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus, Search, X } from 'lucide-react'
import api from '@/services/api'

type CatalogAsset = { id: number; ticker: string; name: string | null; asset_type: string; currency?: string }
type ComparisonAsset = CatalogAsset & {
  currency: string
  last_price: number | null
  last_price_updated_at: string | null
  enrichment: Record<string, unknown>
}

const sections: Array<{ key: string; title: string }> = [
  { key: 'stock_fundamentals', title: 'Fundamentos de ações' },
  { key: 'fii_indicators', title: 'Indicadores de FIIs' },
  { key: 'etf_indicators', title: 'Indicadores de ETFs' },
  { key: 'bdr_indicators', title: 'Indicadores de BDRs' },
  { key: 'crypto_indicators', title: 'Indicadores de criptoativos' },
  { key: 'treasury_indicators', title: 'Indicadores de Tesouro' },
  { key: 'international_profile', title: 'Perfil internacional' },
  { key: 'dividend_metrics', title: 'Proventos (12 meses)' },
]

const labels: Record<string, string> = {
  pe: 'P/L', forward_pe: 'P/L projetado', pb: 'P/VP', dividend_yield: 'Dividend yield', eps: 'LPA',
  market_cap: 'Valor de mercado', enterprise_value: 'Valor da firma', enterprise_to_ebitda: 'EV/EBITDA',
  net_revenue: 'Receita líquida', net_income: 'Lucro líquido', ebitda: 'EBITDA', net_margin: 'Margem líquida',
  operating_margin: 'Margem operacional', gross_margin: 'Margem bruta', roe: 'ROE', roa: 'ROA', net_debt: 'Dívida líquida',
  total_debt: 'Dívida total', free_cash_flow: 'Fluxo de caixa livre', book_value: 'Valor patrimonial', peg_ratio: 'PEG',
  beta: 'Beta', sector: 'Setor', industry: 'Indústria', description: 'Descrição', website: 'Site', employees: 'Funcionários',
  recommendation: 'Recomendação', target_price: 'Preço-alvo', pvp: 'P/VP', dividend_yield_1m: 'DY (1 mês)', net_worth: 'Patrimônio líquido',
  nav_per_share: 'Valor patrimonial por cota', share_holders: 'Cotistas', shares_outstanding: 'Cotas emitidas',
  physical_vacancy: 'Vacância física', financial_vacancy: 'Vacância financeira', properties_count: 'Imóveis', total_area_m2: 'Área total (m²)',
  segment: 'Segmento', segment_type: 'Tipo de segmento', management_type: 'Gestão', administrator_name: 'Administradora', administrator_cnpj: 'CNPJ da administradora',
  symbol: 'Código', benchmark: 'Índice de referência', expense_ratio: 'Taxa de administração', manager: 'Gestor', administrator: 'Administrador',
  dividend_policy: 'Política de proventos', net_assets: 'Patrimônio', category: 'Categoria', underlying_ticker: 'Ativo subjacente',
  underlying_company: 'Empresa subjacente', origin_market: 'Mercado de origem', origin_currency: 'Moeda de origem', depositary_bank: 'Banco depositário',
  ratio: 'Proporção do BDR', coin: 'Criptoativo', coin_name: 'Nome', price_usd: 'Preço (USD)', price_brl: 'Preço (BRL)',
  change_24h_pct: 'Variação 24h', volume_24h: 'Volume 24h', market_cap_brl: 'Valor de mercado (BRL)', market_cap_rank: 'Posição por valor de mercado',
  day_low: 'Mínima do dia', day_high: 'Máxima do dia', currency_rate_usd: 'Câmbio USD', bond_type: 'Tipo de título', name: 'Nome',
  indexer: 'Indexador', coupon_type: 'Cupom', maturity_date: 'Vencimento', duration_days: 'Prazo (dias)', buy_rate: 'Taxa de compra',
  sell_rate: 'Taxa de venda', buy_price: 'Preço de compra', sell_price: 'Preço de venda', base_price: 'Preço base', country: 'País', currency: 'Moeda',
  exchange: 'Bolsa', weburl: 'Site', market_cap_usd: 'Valor de mercado (USD)', consensus: 'Consenso', strong_buy: 'Compra forte', buy: 'Compra',
  hold: 'Manter', sell: 'Venda', strong_sell: 'Venda forte', total_paid_12m: 'Total pago', payments_count_12m: 'Pagamentos',
  last_payment_date: 'Último pagamento', frequency: 'Frequência', dy_12m: 'DY (12 meses)',
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return 'Indisponível'
  if (typeof value === 'boolean') return value ? 'Sim' : 'Não'
  if (typeof value === 'number') return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 4 }).format(value)
  if (Array.isArray(value)) return value.length ? `${value.length} registros` : 'Sem registros'
  if (typeof value === 'object') return Object.entries(value as Record<string, unknown>).map(([key, item]) => `${labels[key] ?? key}: ${formatValue(item)}`).join(' · ')
  return String(value)
}

export default function AssetComparisonPage() {
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<CatalogAsset[]>([])
  const normalizedSearch = search.trim()
  const { data: matches = [], isFetching } = useQuery<CatalogAsset[]>({
    queryKey: ['asset-comparison-search', normalizedSearch],
    queryFn: () => api.get('/assets/search', { params: { q: normalizedSearch, limit: 12 } }).then(response => response.data),
    enabled: normalizedSearch.length >= 2,
    staleTime: 60_000,
  })
  const selectedIds = selected.map(asset => asset.id)
  const { data: comparison = [], isFetching: loadingComparison, error } = useQuery<ComparisonAsset[]>({
    queryKey: ['asset-comparison', selectedIds],
    queryFn: () => api.post('/assets/comparison', { asset_ids: selectedIds }).then(response => response.data),
    enabled: selectedIds.length >= 2,
    staleTime: 60_000,
  })
  const comparisonById = useMemo(() => new Map(comparison.map(asset => [asset.id, asset])), [comparison])

  function addAsset(asset: CatalogAsset) {
    if (selected.length >= 6 || selected.some(item => item.id === asset.id)) return
    setSelected(current => [...current, asset])
    setSearch('')
  }

  return (
    <div className="page-container space-y-5">
      <header>
        <h1 className="page-title">Comparar ativos</h1>
        <p className="mt-1 text-sm" style={{ color: 'var(--color-text-muted)' }}>
          Pesquise no catálogo e compare fundamentos e indicadores disponíveis. A comparação não consulta provedores externos.
        </p>
      </header>

      <section className="card p-4 sm:p-5" aria-label="Selecionar ativos">
        <label htmlFor="asset-comparison-search" className="mb-2 block text-sm font-medium">Adicionar ativo ({selected.length}/6)</label>
        <div className="relative max-w-xl">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--color-text-faint)' }} />
          <input id="asset-comparison-search" className="input w-full pl-9" value={search} onChange={event => setSearch(event.target.value)} placeholder="Busque por ticker ou nome" autoComplete="off" />
        </div>
        {normalizedSearch.length >= 2 && (
          <div className="mt-2 max-w-xl overflow-hidden rounded-lg border" style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface-2)' }}>
            {isFetching ? <p className="p-3 text-sm">Buscando no catálogo…</p> : matches.filter(asset => !selectedIds.includes(asset.id)).map(asset => (
              <button key={asset.id} type="button" onClick={() => addAsset(asset)} disabled={selected.length >= 6} className="flex w-full items-center gap-2 border-b p-3 text-left text-sm last:border-0 hover:bg-black/5">
                <Plus size={15} /><span className="font-semibold">{asset.ticker}</span><span>{asset.name}</span><span className="ml-auto text-xs">{asset.asset_type}</span>
              </button>
            ))}
            {!isFetching && matches.filter(asset => !selectedIds.includes(asset.id)).length === 0 && <p className="p-3 text-sm">Nenhum ativo disponível no catálogo.</p>}
          </div>
        )}
        {selected.length > 0 && <div className="mt-4 flex flex-wrap gap-2">{selected.map(asset => (
          <span key={asset.id} className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm" style={{ borderColor: 'var(--color-border)' }}>
            <strong>{asset.ticker}</strong><span>{asset.name}</span>
            <button type="button" aria-label={`Remover ${asset.ticker}`} onClick={() => setSelected(current => current.filter(item => item.id !== asset.id))}><X size={14} /></button>
          </span>
        ))}</div>}
      </section>

      {selected.length < 2 ? <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Selecione pelo menos dois ativos para iniciar a comparação.</p> : (
        <section className="card overflow-hidden" aria-label="Matriz de comparação">
          {loadingComparison && <p className="p-4 text-sm">Carregando dados disponíveis…</p>}
          {error && <p role="alert" className="p-4 text-sm text-red-500">Não foi possível carregar a comparação. Tente novamente.</p>}
          {!loadingComparison && <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse text-sm">
              <thead><tr><th className="sticky left-0 p-3 text-left" style={{ background: 'var(--color-surface-2)' }}>Dado</th>{selected.map(asset => <th key={asset.id} className="min-w-44 p-3 text-left" style={{ background: 'var(--color-surface-2)' }}>{asset.ticker}<span className="block text-xs font-normal">{asset.name}</span></th>)}</tr></thead>
              <tbody>
                <tr className="border-t" style={{ borderColor: 'var(--color-border)' }}><th className="sticky left-0 p-3 text-left" style={{ background: 'var(--color-surface)' }}>Classe / moeda</th>{selected.map(asset => <td key={asset.id} className="p-3">{asset.asset_type} · {asset.currency ?? '—'}</td>)}</tr>
                <tr className="border-t" style={{ borderColor: 'var(--color-border)' }}><th className="sticky left-0 p-3 text-left" style={{ background: 'var(--color-surface)' }}>Último preço</th>{selected.map(asset => { const data = comparisonById.get(asset.id); return <td key={asset.id} className="p-3">{data?.last_price == null ? 'Indisponível' : `${formatValue(data.last_price)} ${data.currency}`}<span className="block text-xs" style={{ color: 'var(--color-text-muted)' }}>{data?.last_price_updated_at ? new Date(data.last_price_updated_at).toLocaleString('pt-BR') : 'Data indisponível'}</span></td> })}</tr>
                <tr className="border-t" style={{ borderColor: 'var(--color-border)' }}><th className="sticky left-0 p-3 text-left" style={{ background: 'var(--color-surface)' }}>Cobertura</th>{selected.map(asset => <td key={asset.id} className="p-3">{formatValue(comparisonById.get(asset.id)?.enrichment.coverage_status)}</td>)}</tr>
                <tr className="border-t" style={{ borderColor: 'var(--color-border)' }}><th className="sticky left-0 p-3 text-left" style={{ background: 'var(--color-surface)' }}>Capacidades disponíveis</th>{selected.map(asset => <td key={asset.id} className="p-3">{formatValue(comparisonById.get(asset.id)?.enrichment.capabilities)}</td>)}</tr>
                <tr className="border-t" style={{ borderColor: 'var(--color-border)' }}><th className="sticky left-0 p-3 text-left" style={{ background: 'var(--color-surface)' }}>Histórico de proventos em cache</th>{selected.map(asset => {
                  const history = comparisonById.get(asset.id)?.enrichment.dividend_history
                  return <td key={asset.id} className="p-3">{Array.isArray(history) && history.length ? <details><summary className="cursor-pointer">{history.length} registros</summary><pre className="mt-2 max-w-xs overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(history, null, 2)}</pre></details> : 'Sem registros disponíveis'}</td>
                })}</tr>
              </tbody>
                {sections.map(section => {
                  const rows = new Set<string>()
                  selected.forEach(asset => {
                    const value = comparisonById.get(asset.id)?.enrichment[section.key]
                    if (value && typeof value === 'object' && !Array.isArray(value)) Object.keys(value).forEach(key => rows.add(key))
                  })
                  if (!rows.size) return null
                  return <tbody key={section.key}>
                    <tr><th colSpan={selected.length + 1} className="p-3 text-left font-semibold" style={{ background: 'var(--color-surface-2)' }}>{section.title}</th></tr>
                    {[...rows].map(key => <tr key={key} className="border-t" style={{ borderColor: 'var(--color-border)' }}><th className="sticky left-0 p-3 text-left font-medium" style={{ background: 'var(--color-surface)' }}>{labels[key] ?? key}</th>{selected.map(asset => {
                      const record = comparisonById.get(asset.id)?.enrichment[section.key] as Record<string, unknown> | null | undefined
                      return <td key={asset.id} className="p-3">{formatValue(record?.[key])}</td>
                    })}</tr>)}
                  </tbody>
                })}
            </table>
          </div>}
          <p className="border-t p-3 text-xs" style={{ color: 'var(--color-text-muted)', borderColor: 'var(--color-border)' }}>Campos indisponíveis não possuem valor armazenado no cache. Os indicadores exibidos são informativos e podem ter datas de referência diferentes.</p>
        </section>
      )}
    </div>
  )
}
