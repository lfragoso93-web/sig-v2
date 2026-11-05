import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, ArrowDownToLine, CalendarDays, ChartNoAxesCombined, CircleDollarSign, FileText, Search } from 'lucide-react'
import api from '@/services/api'

type CatalogAsset = { id: number; ticker: string; name: string | null; asset_type: string }
type DataRow = Record<string, unknown>
type AssetAnalysis = {
  asset: DataRow
  enrichment: DataRow
  price_history: DataRow[]
  dividends: DataRow[]
  corporate_events: DataRow[]
  reports: DataRow[]
}

const labels: Record<string, string> = {
  ticker: 'Código', asset_class: 'Classe de ativo', coverage_status: 'Cobertura de dados',
  capabilities: 'Dados disponíveis', stock_fundamentals: 'Fundamentos de ações', fii_indicators: 'Indicadores de FIIs',
  etf_indicators: 'Indicadores de ETFs', bdr_indicators: 'Indicadores de BDRs', crypto_indicators: 'Indicadores de criptoativos',
  treasury_indicators: 'Indicadores do Tesouro', international_profile: 'Perfil internacional', dividend_metrics: 'Métricas de proventos',
  pe: 'Preço / lucro (P/L)', forward_pe: 'P/L projetado', pb: 'Preço / valor patrimonial (P/VP)', pvp: 'Preço / valor patrimonial (P/VP)',
  dividend_yield: 'Dividend yield', dividend_yield_1m: 'Dividend yield (1 mês)', dy_12m: 'Dividend yield (12 meses)',
  eps: 'Lucro por ação (LPA)', market_cap: 'Valor de mercado', market_cap_brl: 'Valor de mercado (BRL)',
  market_cap_usd: 'Valor de mercado (USD)', enterprise_value: 'Valor da firma', enterprise_to_ebitda: 'EV / EBITDA',
  net_revenue: 'Receita líquida', net_income: 'Lucro líquido', ebitda: 'EBITDA', net_margin: 'Margem líquida',
  operating_margin: 'Margem operacional', gross_margin: 'Margem bruta', roe: 'Retorno sobre patrimônio (ROE)',
  roa: 'Retorno sobre ativos (ROA)', net_debt: 'Dívida líquida', total_debt: 'Dívida total', free_cash_flow: 'Fluxo de caixa livre',
  book_value: 'Valor patrimonial', peg_ratio: 'PEG', beta: 'Beta', sector: 'Setor', sub_sector: 'Subsetor', industry: 'Indústria',
  description: 'Descrição', website: 'Site', employees: 'Funcionários', recommendation: 'Recomendação', target_price: 'Preço-alvo',
  net_worth: 'Patrimônio líquido', nav_per_share: 'Valor patrimonial por cota', share_holders: 'Cotistas', shares_outstanding: 'Cotas emitidas',
  physical_vacancy: 'Vacância física', financial_vacancy: 'Vacância financeira', properties_count: 'Imóveis', total_area_m2: 'Área total (m²)',
  segment: 'Segmento', segment_type: 'Tipo de segmento', management_type: 'Gestão', administrator_name: 'Administradora',
  administrator_cnpj: 'CNPJ da administradora', symbol: 'Código', benchmark: 'Índice de referência', expense_ratio: 'Taxa de administração',
  manager: 'Gestor', administrator: 'Administrador', dividend_policy: 'Política de proventos', net_assets: 'Patrimônio', category: 'Categoria',
  underlying_ticker: 'Ativo subjacente', underlying_company: 'Empresa subjacente', origin_market: 'Mercado de origem',
  origin_currency: 'Moeda de origem', depositary_bank: 'Banco depositário', ratio: 'Proporção do BDR', coin: 'Criptoativo',
  coin_name: 'Nome', price_usd: 'Preço (USD)', price_brl: 'Preço (BRL)', change_24h_pct: 'Variação em 24 horas',
  volume_24h: 'Volume negociado (24 horas)', market_cap_rank: 'Posição por valor de mercado', day_low: 'Mínima do dia',
  day_high: 'Máxima do dia', currency_rate_usd: 'Câmbio para USD', bond_type: 'Tipo de título', indexer: 'Indexador',
  coupon_type: 'Cupom', maturity_date: 'Vencimento', duration_days: 'Prazo (dias)', buy_rate: 'Taxa de compra',
  sell_rate: 'Taxa de venda', buy_price: 'Preço de compra', sell_price: 'Preço de venda', base_price: 'Preço base',
  country: 'País', currency: 'Moeda', exchange: 'Bolsa', weburl: 'Site', consensus: 'Consenso', strong_buy: 'Compra forte',
  buy: 'Compra', hold: 'Manter', sell: 'Venda', strong_sell: 'Venda forte', total_paid_12m: 'Total pago em 12 meses',
  payments_count_12m: 'Pagamentos em 12 meses', last_payment_date: 'Data do último pagamento', frequency: 'Frequência',
  timestamp: 'Data', open: 'Abertura', high: 'Máxima', low: 'Mínima', close: 'Fechamento', volume: 'Volume', source: 'Fonte',
  record_date: 'Data-base', ex_date: 'Data ex', payment_date: 'Pagamento', type: 'Tipo', value_per_unit: 'Valor por unidade', remarks: 'Observações',
  event_type: 'Tipo de evento', status: 'Situação', reconciliation_status: 'Conciliação', requires_review: 'Requer revisão',
  effective_date: 'Data de vigência', announcement_date: 'Anúncio', source_provider: 'Fonte',
  provider: 'Provedor', provider_status: 'Situação do provedor', provider_last_sync_at: 'Última sincronização',
  isin_code: 'ISIN', last_price: 'Último preço', last_price_updated_at: 'Atualizado em',
}

const moneyFields = new Set([
  'last_price', 'open', 'high', 'low', 'close', 'value_per_unit', 'target_price', 'buy_price', 'sell_price', 'base_price',
  'market_cap', 'market_cap_brl', 'market_cap_usd', 'enterprise_value', 'net_revenue', 'net_income', 'ebitda', 'net_debt',
  'total_debt', 'free_cash_flow', 'book_value', 'net_worth', 'nav_per_share', 'net_assets', 'total_paid_12m', 'price_usd',
  'price_brl', 'day_low', 'day_high', 'eps',
])
const percentFields = new Set([
  'dividend_yield', 'dividend_yield_1m', 'dy_12m', 'net_margin', 'operating_margin', 'gross_margin', 'roe', 'roa',
  'physical_vacancy', 'financial_vacancy', 'expense_ratio', 'change_24h_pct', 'buy_rate', 'sell_rate',
])
const dateFields = new Set(['timestamp', 'record_date', 'ex_date', 'payment_date', 'effective_date', 'announcement_date', 'maturity_date', 'last_payment_date'])
const enumFields = new Set(['asset_type', 'asset_class', 'type', 'event_type', 'status', 'reconciliation_status', 'provider_status', 'coverage_status'])

function safeDate(value: unknown): string {
  if (typeof value !== 'string' || !value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const options: Intl.DateTimeFormatOptions = value.includes('T')
    ? { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo' }
    : { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' }
  return date.toLocaleString('pt-BR', options)
}

function money(value: number, currency: string): string {
  try {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency, maximumFractionDigits: 8 }).format(value)
  } catch {
    return `${new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 8 }).format(value)} ${currency}`
  }
}

function formatField(key: string, value: unknown, currency = 'BRL'): string {
  if (value === null || value === undefined || value === '') return '—'
  if (dateFields.has(key) || key.endsWith('_at')) return safeDate(value)
  if (typeof value === 'boolean') return value ? 'Sim' : 'Não'
  if (typeof value === 'number') {
    const explicitCurrency = key === 'total_paid_12m' || key.endsWith('_brl') ? 'BRL' : key.endsWith('_usd') ? 'USD' : currency
    if (moneyFields.has(key) || key.startsWith('price_')) return money(value, explicitCurrency)
    if (percentFields.has(key)) return `${new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 3 }).format(value)}%`
    return new Intl.NumberFormat('pt-BR', { maximumSignificantDigits: 8 }).format(value)
  }
  if (Array.isArray(value)) return value.length ? `${value.length} registros` : 'Nenhum registro'
  if (typeof value === 'object') return Object.entries(value as DataRow).map(([childKey, childValue]) => `${labels[childKey] ?? humanize(childKey)}: ${formatField(childKey, childValue, currency)}`).join(' · ')
  if (typeof value === 'string' && enumFields.has(key)) return displayEnum(value)
  return String(value)
}

function humanize(key: string): string {
  return labels[key] ?? key.split('_').map(part => part.charAt(0).toUpperCase() + part.slice(1)).join(' ')
}

function displayEnum(value: string): string {
  const known: Record<string, string> = {
    ACAO: 'Ação', ETF_NACIONAL: 'ETF nacional', ETF_INTERNACIONAL: 'ETF internacional', STOCK: 'Ação internacional',
    CRIPTO: 'Criptoativo', TESOURO_DIRETO: 'Tesouro Direto', RENDA_FIXA: 'Renda fixa', FII: 'Fundo imobiliário', BDR: 'BDR',
    DIVIDENDO: 'Dividendo', JCP: 'Juros sobre capital próprio', RENDIMENTO: 'Rendimento', AMORTIZACAO: 'Amortização',
    BONIFICACAO: 'Bonificação', SUBSCRICAO: 'Subscrição', OUTROS: 'Outros', REVERSE_SPLIT: 'Grupamento',
    SPLIT: 'Desdobramento', BONUS: 'Bonificação', RIGHTS: 'Direito de subscrição', PENDENTE: 'Pendente',
    MATCHED: 'Conciliado', UNRECONCILED: 'A conciliar', CONFLICT: 'Divergente',
  }
  const readable = value.replace(/_/g, ' ').toLocaleLowerCase('pt-BR')
  return known[value.toUpperCase()] ?? readable.charAt(0).toLocaleUpperCase('pt-BR') + readable.slice(1)
}

function availableSections(data: AssetAnalysis) {
  const fundamentals = Object.entries(data.enrichment).filter(([key, value]) =>
    !['ticker', 'asset_class', 'coverage_status', 'capabilities', 'dividend_history', 'dividend_metrics'].includes(key) && value !== null && value !== undefined && value !== '' &&
    (!(typeof value === 'object') || Array.isArray(value) || Object.values(value as DataRow).some(item => item !== null && item !== undefined && item !== '')),
  )
  return fundamentals
}

function DataTable({ title, rows, currency, empty }: { title: string; rows: DataRow[]; currency: string; empty: string }) {
  const keys = Array.from(new Set(rows.flatMap(row => Object.keys(row))))
  return <section className="card overflow-hidden">
    <div className="flex flex-wrap items-center justify-between gap-2 border-b px-4 py-3" style={{ borderColor: 'var(--color-border)' }}>
      <h3 className="font-semibold">{title}</h3><span className="rounded-full px-2.5 py-1 text-xs" style={{ background: 'var(--color-surface-2)', color: 'var(--color-text-muted)' }}>{rows.length} registros</span>
    </div>
    {!rows.length ? <p className="p-5 text-sm" style={{ color: 'var(--color-text-muted)' }}>{empty}</p> :
      <div className="overflow-x-auto"><table className="w-full min-w-max text-left text-sm">
        <thead><tr style={{ color: 'var(--color-text-muted)', background: 'var(--color-surface-2)' }}>{keys.map(key => <th key={key} className="px-4 py-3 font-medium">{humanize(key)}</th>)}</tr></thead>
        <tbody>{rows.map((row, index) => <tr key={index} className="border-t" style={{ borderColor: 'var(--color-border)' }}>{keys.map(key => <td key={key} className="max-w-sm px-4 py-3 align-top tabular-nums">{formatField(key, row[key], currency)}</td>)}</tr>)}</tbody>
      </table></div>}
  </section>
}

function MetricCard({ name, value, currency }: { name: string; value: unknown; currency: string }) {
  return <div className="min-w-0 rounded-lg border p-3" style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface-2)' }}>
    <dt className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{humanize(name)}</dt>
    <dd className="mt-1 break-words text-sm font-semibold tabular-nums">{formatField(name, value, currency)}</dd>
  </div>
}

function SectionLink({ href, icon: Icon, children, count }: { href: string; icon: typeof Activity; children: string; count?: number }) {
  return <a href={href} className="flex shrink-0 items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors hover:bg-black/5" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}>
    <Icon size={15} />{children}{count !== undefined && <span className="rounded-full px-1.5 text-xs" style={{ background: 'var(--color-surface-2)' }}>{count}</span>}
  </a>
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
  const currency = String(data?.asset.currency || 'BRL').toUpperCase()
  const fundamentals = data ? availableSections(data) : []
  const coverage = String(data?.enrichment.coverage_status ?? 'UNKNOWN').toUpperCase()
  const coverageLabel = coverage === 'FULL' ? 'completa' : coverage === 'PARTIAL' ? 'parcial' : coverage === 'UNSUPPORTED' ? 'não suportada' : 'ainda não avaliada'
  const catalogFields: Array<[string, string, unknown]> = data ? ([
    ['Classe', 'asset_type', data.asset.asset_type], ['Setor', 'sector', data.asset.sector], ['Subsetor', 'sub_sector', data.asset.sub_sector], ['ISIN', 'isin_code', data.asset.isin_code],
    ['Provedor', 'provider', data.asset.provider], ['Situação do provedor', 'provider_status', data.asset.provider_status],
  ] as Array<[string, string, unknown]>).filter(([, , value]) => value !== null && value !== undefined && value !== '') : []

  return <div className="page-container space-y-5 pb-10">
    <header>
      <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em]" style={{ color: 'var(--color-primary)' }}>Ferramentas · Pesquisa</p>
      <h1 className="page-title">Análise de ativos</h1>
      <p className="mt-1 max-w-3xl text-sm" style={{ color: 'var(--color-text-muted)' }}>Consulte em um só lugar os fundamentos, cotações históricas, proventos e eventos registrados no sistema.</p>
    </header>

    <section className="card p-4 sm:p-5">
      <label htmlFor="asset-analysis-search" className="mb-2 block text-sm font-medium">Encontre um ativo no catálogo</label>
      <div className="relative max-w-2xl"><Search size={17} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--color-text-faint)' }} /><input id="asset-analysis-search" className="input w-full pl-10" value={search} onChange={event => { setSearch(event.target.value); setSelected(null) }} placeholder="Busque por ticker ou nome, por exemplo PETR4 ou Bitcoin" autoComplete="off" /></div>
      {normalized.length >= 2 && <div className="mt-2 max-w-2xl overflow-hidden rounded-lg border" style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface)' }}>
        {isFetching ? <p className="p-3 text-sm" style={{ color: 'var(--color-text-muted)' }}>Buscando no catálogo…</p> : matches.map(asset => <button key={asset.id} type="button" className="block w-full border-b p-3 text-left text-sm last:border-0 hover:bg-black/5" style={{ borderColor: 'var(--color-border)' }} onClick={() => { setSelected(asset); setSearch(asset.ticker + ' — ' + (asset.name ?? asset.asset_type)) }}><span className="font-semibold">{asset.ticker}</span><span style={{ color: 'var(--color-text-muted)' }}> — {asset.name ?? asset.asset_type}</span></button>)}
        {!isFetching && !matches.length && <p className="p-3 text-sm" style={{ color: 'var(--color-text-muted)' }}>Nenhum ativo encontrado no catálogo.</p>}
      </div>}
    </section>

    {isLoading && <p role="status" className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Carregando dados disponíveis…</p>}
    {isError && <p role="alert" className="rounded-lg border border-red-500/30 p-3 text-sm text-red-400">Não foi possível carregar os dados deste ativo. Tente novamente.</p>}
    {!selected && !isLoading && <section className="card flex flex-col items-center px-5 py-12 text-center">
      <div className="mb-3 rounded-full p-3" style={{ background: 'var(--color-surface-2)', color: 'var(--color-primary)' }}><ChartNoAxesCombined size={24} /></div>
      <h2 className="font-semibold">Escolha um ativo para começar</h2><p className="mt-1 max-w-md text-sm" style={{ color: 'var(--color-text-muted)' }}>A análise reúne os dados existentes no catálogo. A abertura desta página não inicia consultas a provedores.</p>
    </section>}

    {data && <>
      <section className="card overflow-hidden">
        <div className="flex flex-col justify-between gap-5 p-5 sm:flex-row sm:items-start sm:p-6">
          <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h2 className="text-2xl font-bold tracking-tight">{String(data.asset.ticker)}</h2><span className="rounded-full px-2.5 py-1 text-xs font-medium" style={{ background: coverage === 'FULL' ? 'rgb(34 197 94 / 12%)' : 'var(--color-surface-2)', color: coverage === 'FULL' ? 'var(--color-success)' : 'var(--color-text-muted)' }}>Cobertura {coverageLabel}</span></div>
            <p className="mt-1 text-sm" style={{ color: 'var(--color-text-muted)' }}>{String(data.asset.name ?? 'Nome não informado')} · Moeda de negociação: {currency}</p>
            <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs" style={{ color: 'var(--color-text-muted)' }}>{catalogFields.map(([label, field, value]) => <span key={field}><span className="font-medium" style={{ color: 'var(--color-text)' }}>{label}:</span> {formatField(field, value, currency)}</span>)}</div>
          </div>
          <div className="shrink-0 rounded-xl p-4 sm:min-w-52 sm:text-right" style={{ background: 'var(--color-surface-2)' }}>
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Último preço registrado</p>
            <p className="mt-1 text-2xl font-bold tabular-nums">{data.asset.last_price == null ? '—' : money(Number(data.asset.last_price), currency)}</p>
            <p className="mt-1 text-xs" style={{ color: 'var(--color-text-muted)' }}>{data.asset.last_price_updated_at ? `Referência: ${safeDate(data.asset.last_price_updated_at)}` : 'Data de referência indisponível'}</p>
          </div>
        </div>
        <div className="flex items-start gap-2 border-t px-5 py-3 text-xs" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}><Activity size={14} className="mt-0.5 shrink-0" /><p>Dados informativos armazenados no sistema. Cada seção pode ter uma data de referência própria; valores e indicadores não representam recomendação de investimento.</p></div>
      </section>

      <nav aria-label="Seções da análise" className="flex gap-2 overflow-x-auto pb-1">
        <SectionLink href="#fundamentos" icon={CircleDollarSign}>Fundamentos</SectionLink>
        <SectionLink href="#historico" icon={ChartNoAxesCombined} count={data.price_history.length}>Histórico</SectionLink>
        <SectionLink href="#proventos" icon={ArrowDownToLine} count={data.dividends.length}>Proventos</SectionLink>
        <SectionLink href="#eventos" icon={CalendarDays} count={data.corporate_events.length}>Eventos</SectionLink>
        <SectionLink href="#relatorios" icon={FileText} count={data.reports.length}>Relatórios</SectionLink>
      </nav>

      <section id="fundamentos" className="scroll-mt-6 space-y-4">
        <div><h2 className="text-lg font-semibold">Fundamentos e indicadores</h2><p className="mt-1 text-sm" style={{ color: 'var(--color-text-muted)' }}>Indicadores disponíveis para a classe deste ativo, conforme o último enriquecimento armazenado.</p></div>
        {!fundamentals.length && !data.enrichment.dividend_metrics ? <div className="card p-5 text-sm" style={{ color: 'var(--color-text-muted)' }}>Ainda não há fundamentos armazenados para este ativo.</div> : <div className="grid gap-4 xl:grid-cols-2">
          {fundamentals.map(([key, value]) => <section key={key} className="card p-4 sm:p-5"><h3 className="mb-3 font-semibold">{humanize(key)}</h3>
            {typeof value === 'object' && value !== null && !Array.isArray(value) ? <dl className="grid gap-2 sm:grid-cols-2">{Object.entries(value as DataRow).filter(([, item]) => item !== null && item !== undefined && item !== '').map(([field, fieldValue]) => <MetricCard key={field} name={field} value={fieldValue} currency={currency} />)}</dl> : <p className="text-sm">{formatField(key, value, currency)}</p>}
          </section>)}
          {data.enrichment.dividend_metrics != null && <section className="card p-4 sm:p-5"><h3 className="mb-3 font-semibold">Proventos (12 meses)</h3><dl className="grid gap-2 sm:grid-cols-2">{Object.entries(data.enrichment.dividend_metrics as DataRow).filter(([, item]) => item !== null && item !== undefined && item !== '').map(([field, value]) => <MetricCard key={field} name={field} value={value} currency={currency} />)}</dl></section>}
        </div>}
        {data.enrichment.capabilities != null && <section className="card p-4 sm:p-5"><h3 className="mb-3 font-semibold">Cobertura por tipo de dado</h3><dl className="grid gap-2 sm:grid-cols-2">{Object.entries(data.enrichment.capabilities as DataRow).map(([field, value]) => <MetricCard key={field} name={field} value={value} currency={currency} />)}</dl></section>}
      </section>

      <section id="historico" className="scroll-mt-6 space-y-3"><div><h2 className="text-lg font-semibold">Histórico de preços</h2><p className="mt-1 text-sm" style={{ color: 'var(--color-text-muted)' }}>Até 90 registros persistidos, em ordem cronológica. Valores na moeda de negociação ({currency}).</p></div>
        <DataTable title="Cotações" rows={data.price_history} currency={currency} empty="Não há cotações históricas armazenadas para este ativo." />
      </section>

      <section id="proventos" className="scroll-mt-6 space-y-3"><div><h2 className="text-lg font-semibold">Proventos</h2><p className="mt-1 text-sm" style={{ color: 'var(--color-text-muted)' }}>Eventos monetários cadastrados e respectivos valores por unidade.</p></div>
        <DataTable title="Proventos registrados" rows={data.dividends} currency={currency} empty="Não há proventos armazenados para este ativo." />
      </section>

      <section id="eventos" className="scroll-mt-6 space-y-3"><div><h2 className="text-lg font-semibold">Eventos corporativos</h2><p className="mt-1 text-sm" style={{ color: 'var(--color-text-muted)' }}>Eventos gerais do ativo que não estão vinculados a uma carteira específica.</p></div>
        <DataTable title="Eventos registrados" rows={data.corporate_events} currency={currency} empty="Não há eventos corporativos gerais armazenados para este ativo." />
      </section>

      <section id="relatorios" className="scroll-mt-6 space-y-3"><div><h2 className="text-lg font-semibold">Relatórios gerenciais</h2><p className="mt-1 text-sm" style={{ color: 'var(--color-text-muted)' }}>Documentos vinculados diretamente a este ativo.</p></div>
        <div className="card p-5">{data.reports.length ? <p className="text-sm">Há {data.reports.length} relatório(s) disponível(is).</p> : <div className="flex items-start gap-3"><div className="rounded-lg p-2" style={{ background: 'var(--color-surface-2)', color: 'var(--color-text-muted)' }}><FileText size={18} /></div><div><p className="font-medium">Nenhum relatório vinculado</p><p className="mt-1 text-sm" style={{ color: 'var(--color-text-muted)' }}>O sistema ainda não possui relatórios gerenciais anexados a este ativo.</p></div></div>}</div>
      </section>
    </>}
  </div>
}
