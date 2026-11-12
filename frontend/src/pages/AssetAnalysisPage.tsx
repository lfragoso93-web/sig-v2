import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  AlertTriangle,
  ArrowDownToLine,
  CalendarDays,
  ChartNoAxesCombined,
  CheckCircle2,
  CircleDollarSign,
  ExternalLink,
  FileText,
  Newspaper,
  Search,
  Sparkles,
  X,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import api from '@/services/api'

type CatalogAsset = { id: number; ticker: string; name: string | null; asset_type: string; currency?: string }
type DataRow = Record<string, unknown>
type ReportItem = {
  id?: string
  title?: string
  category?: string
  reference_date?: string
  delivery_date?: string
  status?: string
  version?: string | number
  fund_name?: string
  source?: string
  url?: string
  download_url?: string
  is_management_report?: boolean
}
type NewsItem = {
  title?: string
  source?: string
  url?: string
  published_at?: string | null
  summary?: string | null
}
type AiAnalysis = {
  ticker?: string
  asset_type?: string
  score?: number
  verdict_label?: string
  executive_summary?: string
  strengths?: string[]
  attention_points?: string[]
  report_confrontation?: string[]
  price_trend?: DataRow
  dividend_outlook?: DataRow
  latest_report_referenced?: {
    title?: string | null
    reference_date?: string | null
    delivery_date?: string | null
    url?: string | null
    excerpt_preview?: string | null
  } | null
  provider_mode?: string
  generated_at?: string
  disclaimer?: string
}
type AssetAnalysis = {
  asset: DataRow
  enrichment: DataRow
  price_history: DataRow[]
  dividends: DataRow[]
  corporate_events: DataRow[]
  reports: ReportItem[]
  news?: NewsItem[]
  reports_news_refresh_pending?: boolean
  ai_analysis?: AiAnalysis
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
  administrator_cnpj: 'CNPJ da administradora', cnpj: 'CNPJ do fundo', symbol: 'Código', benchmark: 'Índice de referência', expense_ratio: 'Taxa de administração',
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
  timestamp: 'Data de fechamento', open: 'Abertura', high: 'Máxima', low: 'Mínima', close: 'Fechamento', volume: 'Volume', source: 'Fonte',
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

function safeDate(value: unknown, includeTime = false): string {
  if (typeof value !== 'string' || !value) return '—'
  const raw = value.trim()
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
    const [y, m, d] = raw.split('-').map(Number)
    const dt = new Date(Date.UTC(y, m - 1, d))
    return dt.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' })
  }
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return raw
  const options: Intl.DateTimeFormatOptions = raw.includes('T') && includeTime
    ? { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'America/Sao_Paulo' }
    : { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' }
  return date.toLocaleString('pt-BR', options)
}

function shortChartDate(value: unknown): string {
  if (typeof value !== 'string' || !value) return ''
  const raw = value.slice(0, 10)
  const parts = raw.split('-')
  if (parts.length === 3) {
    return `${parts[2]}/${parts[1]}/${parts[0].slice(2)}`
  }
  return raw
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
  if (key === 'timestamp') return safeDate(value, false)
  if (dateFields.has(key) || key.endsWith('_at')) return safeDate(value, key.endsWith('_at'))
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
    DIVIDENDO: 'Dividendo', DIVIDEND: 'Dividendo', JCP: 'Juros sobre capital próprio', RENDIMENTO: 'Rendimento', AMORTIZACAO: 'Amortização',
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
  return (
    <section className="card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b px-4 py-3" style={{ borderColor: 'var(--color-border)' }}>
        <h3 className="font-semibold text-sm">{title}</h3>
        <span className="rounded-full px-2.5 py-1 text-xs" style={{ background: 'var(--color-surface-2)', color: 'var(--color-text-muted)' }}>{rows.length} registros</span>
      </div>
      {!rows.length ? (
        <p className="p-5 text-sm" style={{ color: 'var(--color-text-muted)' }}>{empty}</p>
      ) : (
        <div className="overflow-x-auto max-h-96">
          <table className="w-full min-w-max text-left text-sm">
            <thead className="sticky top-0 z-10">
              <tr style={{ color: 'var(--color-text-muted)', background: 'var(--color-surface-2)' }}>
                {keys.map(key => <th key={key} className="px-4 py-3 font-medium">{humanize(key)}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index} className="border-t transition-colors hover:bg-[var(--color-surface-offset)]" style={{ borderColor: 'var(--color-border)' }}>
                  {keys.map(key => <td key={key} className="max-w-sm px-4 py-3 align-top tabular-nums">{formatField(key, row[key], currency)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function MetricCard({ name, value, currency }: { name: string; value: unknown; currency: string }) {
  return (
    <div className="min-w-0 rounded-lg border p-3" style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface-2)' }}>
      <dt className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{humanize(name)}</dt>
      <dd className="mt-1 break-words text-sm font-semibold tabular-nums">{formatField(name, value, currency)}</dd>
    </div>
  )
}

function SectionLink({ href, icon: Icon, children, count }: { href: string; icon: typeof Activity; children: string; count?: number }) {
  return (
    <a href={href} className="flex shrink-0 items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors hover:bg-[var(--color-surface-2)]" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}>
      <Icon size={15} />{children}{count !== undefined && <span className="rounded-full px-1.5 text-xs" style={{ background: 'var(--color-surface-2)' }}>{count}</span>}
    </a>
  )
}

function DailyPriceHistorySection({ rows, currency }: { rows: DataRow[]; currency: string }) {
  const [range, setRange] = useState<'30D' | '90D' | '1A' | 'ALL'>('1A')
  const [showTable, setShowTable] = useState(false)

  const chartPoints = useMemo(() => {
    const normalized = rows
      .map(row => {
        const day = String(row.timestamp ?? '').slice(0, 10)
        const closeVal = Number(row.close)
        return {
          ...row,
          day,
          label: shortChartDate(day),
          close: Number.isFinite(closeVal) ? closeVal : 0,
        }
      })
      .filter(point => point.day && point.close > 0)

    if (range === '30D') return normalized.slice(-30)
    if (range === '90D') return normalized.slice(-90)
    if (range === '1A') return normalized.slice(-252)
    return normalized
  }, [rows, range])

  return (
    <section id="historico" className="scroll-mt-6 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Histórico de preços (fechamento diário)</h2>
          <p className="mt-1 text-sm" style={{ color: 'var(--color-text-muted)' }}>
            Cotação única de fechamento por dia em ordem cronológica ({currency}).
          </p>
        </div>
        {rows.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            {(['30D', '90D', '1A', 'ALL'] as const).map(opt => (
              <button
                key={opt}
                type="button"
                onClick={() => setRange(opt)}
                className="rounded-lg px-2.5 py-1 text-xs font-semibold transition-colors"
                style={{
                  background: range === opt ? 'var(--color-primary)' : 'var(--color-surface-2)',
                  color: range === opt ? '#fff' : 'var(--color-text-muted)',
                }}
              >
                {opt === 'ALL' ? 'Tudo' : opt}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setShowTable(v => !v)}
              className="rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}
            >
              {showTable ? 'Ocultar tabela' : 'Ver tabela'}
            </button>
          </div>
        )}
      </div>

      {chartPoints.length > 0 ? (
        <div className="card p-4 sm:p-5 space-y-4">
          <div className="h-64 w-full" aria-label="Gráfico de fechamento diário">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartPoints} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
                <defs>
                  <linearGradient id="assetCloseGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.32} />
                    <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} minTickGap={24} />
                <YAxis
                  domain={['auto', 'auto']}
                  tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
                  tickFormatter={val => money(Number(val), currency)}
                  width={88}
                />
                <Tooltip
                  contentStyle={{
                    background: 'var(--color-surface)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 10,
                    fontSize: 12,
                  }}
                  formatter={(value: unknown) => [money(Number(value), currency), 'Fechamento']}
                  labelFormatter={label => `Data: ${label}`}
                />
                <Area
                  type="monotone"
                  dataKey="close"
                  stroke="var(--color-primary)"
                  strokeWidth={2}
                  fill="url(#assetCloseGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-3 text-xs" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}>
            <span>Último fechamento da série: <strong className="tabular-nums" style={{ color: 'var(--color-text)' }}>{money(chartPoints[chartPoints.length - 1].close, currency)}</strong> ({safeDate(chartPoints[chartPoints.length - 1].day)})</span>
            <span>{chartPoints.length} fechamento(s) diário(s) exibido(s)</span>
          </div>
        </div>
      ) : null}

      {(showTable || chartPoints.length === 0) && (
        <DataTable
          title="Cotações de fechamento diário"
          rows={[...rows].reverse()}
          currency={currency}
          empty="Não há cotações históricas armazenadas para este ativo."
        />
      )}
    </section>
  )
}

function DividendsHistorySection({ rows, currency }: { rows: DataRow[]; currency: string }) {
  const [showTable, setShowTable] = useState(false)

  const chartPoints = useMemo(() => {
    return [...rows]
      .map(row => {
        const rawDate = String(row.payment_date || row.ex_date || row.record_date || '').slice(0, 10)
        const val = Number(row.value_per_unit ?? row.value ?? 0)
        return {
          rawDate,
          label: shortChartDate(rawDate),
          value_per_unit: Number.isFinite(val) ? val : 0,
          type: displayEnum(String(row.type || 'PROVENTO')),
        }
      })
      .filter(item => item.rawDate && item.value_per_unit > 0)
      .sort((a, b) => a.rawDate.localeCompare(b.rawDate))
      .slice(-24)
  }, [rows])

  return (
    <section id="proventos" className="scroll-mt-6 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Proventos</h2>
          <p className="mt-1 text-sm" style={{ color: 'var(--color-text-muted)' }}>
            Evolução gráfica e eventos monetários registrados por unidade ({currency}).
          </p>
        </div>
        {rows.length > 0 && (
          <button
            type="button"
            onClick={() => setShowTable(v => !v)}
            className="rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors"
            style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}
          >
            {showTable ? 'Ocultar tabela' : 'Ver tabela detalhada'}
          </button>
        )}
      </div>

      {chartPoints.length > 0 ? (
        <div className="card p-4 sm:p-5 space-y-4">
          <div className="h-60 w-full" aria-label="Gráfico de histórico de proventos">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartPoints} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} minTickGap={18} />
                <YAxis
                  tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
                  tickFormatter={val => money(Number(val), currency)}
                  width={84}
                />
                <Tooltip
                  contentStyle={{
                    background: 'var(--color-surface)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 10,
                    fontSize: 12,
                  }}
                  formatter={(value: unknown) => [money(Number(value), currency), 'Provento / unid.']}
                  labelFormatter={label => `Data: ${label}`}
                />
                <Bar dataKey="value_per_unit" fill="var(--color-success)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-3 text-xs" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}>
            <span>Último provento: <strong className="tabular-nums" style={{ color: 'var(--color-text)' }}>{money(chartPoints[chartPoints.length - 1].value_per_unit, currency)}</strong> ({chartPoints[chartPoints.length - 1].type})</span>
            <span>{rows.length} evento(s) registrado(s)</span>
          </div>
        </div>
      ) : null}

      {(showTable || chartPoints.length === 0) && (
        <DataTable
          title="Proventos registrados"
          rows={rows}
          currency={currency}
          empty="Não há proventos armazenados para este ativo."
        />
      )}
    </section>
  )
}

function useSafeSearchParams() {
  try {
    return useSearchParams()
  } catch {
    return [new URLSearchParams(), () => {}] as const
  }
}

export default function AssetAnalysisPage() {
  const [searchParams, setSearchParams] = useSafeSearchParams()
  const initialTicker = searchParams.get('ticker')?.trim() || ''
  const initialId = searchParams.get('id')?.trim() || ''
  const urlParam = initialTicker || initialId

  const [search, setSearch] = useState('')
  const [assetTypeFilter, setAssetTypeFilter] = useState('')
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [selected, setSelected] = useState<CatalogAsset | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const normalized = search.trim()

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    if (!urlParam && selected && !isDropdownOpen) {
      setSelected(null)
      setSearch('')
    }
  }, [urlParam, selected, isDropdownOpen])

  const { data: matches = [], isFetching } = useQuery<CatalogAsset[]>({
    queryKey: ['asset-analysis-search', normalized, assetTypeFilter],
    queryFn: () => api.get('/assets/search', { params: { q: normalized, limit: 15, ...(assetTypeFilter ? { asset_type: assetTypeFilter } : {}) } }).then(response => response.data),
    enabled: normalized.length >= 2 && isDropdownOpen,
    staleTime: 60_000,
  })

  const targetIdentifier = urlParam || (selected?.id ? String(selected.id) : null)
  const refreshPollCountRef = useRef(0)

  useEffect(() => {
    refreshPollCountRef.current = 0
  }, [targetIdentifier])

  const { data, isLoading, isError } = useQuery<AssetAnalysis>({
    queryKey: ['asset-analysis', targetIdentifier],
    queryFn: () => api.get('/assets/analysis/' + encodeURIComponent(targetIdentifier!)).then(response => response.data),
    enabled: targetIdentifier !== null,
    staleTime: 60_000,
    refetchInterval: query => {
      const pending = query.state.data?.reports_news_refresh_pending
      if (pending && refreshPollCountRef.current < 5) {
        refreshPollCountRef.current += 1
        return 3_000
      }
      return false
    },
  })

  useEffect(() => {
    if (data?.asset) {
      if (!selected || selected.id !== data.asset.id || selected.ticker !== data.asset.ticker) {
        setSelected(data.asset as CatalogAsset)
        setSearch(String(data.asset.ticker))
      }
    }
  }, [data?.asset, selected])

  function handleSelect(asset: CatalogAsset) {
    setSelected(asset)
    setSearch(asset.ticker)
    setIsDropdownOpen(false)
    setSearchParams({ ticker: asset.ticker })
  }

  function handleClear() {
    setSelected(null)
    setSearch('')
    setIsDropdownOpen(false)
    setSearchParams({})
  }

  const currency = String(data?.asset?.currency || 'BRL').toUpperCase()
  const fundamentals = data?.enrichment ? availableSections(data) : []
  const coverage = String(data?.enrichment?.coverage_status ?? 'UNKNOWN').toUpperCase()
  const coverageLabel = coverage === 'FULL' ? 'completa' : coverage === 'PARTIAL' ? 'parcial' : coverage === 'UNSUPPORTED' ? 'não suportada' : 'ainda não avaliada'
  const catalogFields: Array<[string, string, unknown]> = data?.asset ? ([
    ['Classe', 'asset_type', data.asset.asset_type], ['Setor', 'sector', data.asset.sector], ['Subsetor', 'sub_sector', data.asset.sub_sector], ['ISIN', 'isin_code', data.asset.isin_code],
    ['Provedor', 'provider', data.asset.provider], ['Situação do provedor', 'provider_status', data.asset.provider_status],
  ] as Array<[string, string, unknown]>).filter(([, , value]) => value !== null && value !== undefined && value !== '') : []

  const reports = data?.reports ?? []
  const news = data?.news ?? []
  const aiAnalysis = data?.ai_analysis

  return (
    <div className="page-container space-y-5 pb-10">
      <header>
        <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em]" style={{ color: 'var(--color-primary)' }}>Ferramentas · Pesquisa</p>
        <h1 className="page-title">Análise de ativos</h1>
        <p className="mt-1 max-w-3xl text-sm" style={{ color: 'var(--color-text-muted)' }}>
          Consulte em um só lugar a análise por IA, fundamentos, gráficos de fechamento diário, proventos, relatórios gerenciais (CVM/B3) e notícias do ativo.
        </p>
      </header>

      <section className="card p-4 sm:p-5" ref={containerRef}>
        <label htmlFor="asset-analysis-search" className="mb-2 block text-sm font-medium">Encontre um ativo no catálogo</label>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center max-w-3xl">
          <select
            aria-label="Filtrar por classe"
            className="input sm:w-48"
            value={assetTypeFilter}
            onChange={event => setAssetTypeFilter(event.target.value)}
          >
            <option value="">Todas as classes</option>
            <option value="ACAO">Ações B3</option>
            <option value="FII">FIIs</option>
            <option value="ETF_NACIONAL">ETFs Brasil</option>
            <option value="BDR">BDRs</option>
            <option value="STOCK">Stocks (EUA)</option>
            <option value="ETF_INTERNACIONAL">ETFs Internacionais</option>
            <option value="CRIPTO">Criptomoedas</option>
            <option value="TESOURO_DIRETO">Tesouro Direto</option>
          </select>
          <div className="relative flex-1">
            <Search size={17} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--color-text-faint)' }} />
            <input
              id="asset-analysis-search"
              className="input w-full pl-10 pr-10"
              value={search}
              onChange={event => {
                setSearch(event.target.value)
                setIsDropdownOpen(true)
              }}
              onFocus={() => {
                if (normalized.length >= 2) setIsDropdownOpen(true)
              }}
              placeholder="Busque por ticker ou nome, por exemplo PETR4, MXRF11 ou Bitcoin"
              autoComplete="off"
            />
            {(search || selected) && (
              <button
                type="button"
                onClick={handleClear}
                aria-label="Limpar pesquisa"
                className="absolute right-3 top-1/2 -translate-y-1/2 rounded p-1 transition-colors hover:bg-[var(--color-surface-2)]"
                style={{ color: 'var(--color-text-muted)' }}
              >
                <X size={15} />
              </button>
            )}
          </div>
        </div>

        {isDropdownOpen && normalized.length >= 2 && (
          <div className="mt-2 max-w-2xl overflow-hidden rounded-lg border shadow-lg" style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface)' }}>
            {isFetching ? (
              <p className="p-3 text-sm" style={{ color: 'var(--color-text-muted)' }}>Buscando no catálogo…</p>
            ) : matches.map(asset => (
              <button
                key={asset.id}
                type="button"
                className="block w-full border-b p-3 text-left text-sm last:border-0 transition-colors hover:bg-[var(--color-surface-offset)]"
                style={{ borderColor: 'var(--color-border)' }}
                onClick={() => handleSelect(asset)}
              >
                <span className="font-semibold">{asset.ticker}</span>
                <span style={{ color: 'var(--color-text-muted)' }}> — {asset.name ?? asset.asset_type}</span>
              </button>
            ))}
            {!isFetching && !matches.length && (
              <p className="p-3 text-sm" style={{ color: 'var(--color-text-muted)' }}>Nenhum ativo encontrado no catálogo.</p>
            )}
          </div>
        )}
      </section>

      {isLoading && <p role="status" className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Carregando dados disponíveis…</p>}
      {isError && <p role="alert" className="rounded-lg border border-red-500/30 p-3 text-sm text-red-400">Não foi possível carregar os dados deste ativo. Tente novamente.</p>}

      {!targetIdentifier && !isLoading && (
        <section className="card flex flex-col items-center px-5 py-12 text-center">
          <div className="mb-3 rounded-full p-3" style={{ background: 'var(--color-surface-2)', color: 'var(--color-primary)' }}><ChartNoAxesCombined size={24} /></div>
          <h2 className="font-semibold">Escolha um ativo para começar</h2>
          <p className="mt-1 max-w-md text-sm" style={{ color: 'var(--color-text-muted)' }}>A análise reúne os dados existentes no catálogo, relatórios CVM/B3 e síntese analítica por IA.</p>
        </section>
      )}

      {data?.asset && (
        <>
          <section className="card overflow-hidden">
            <div className="flex flex-col justify-between gap-5 p-5 sm:flex-row sm:items-start sm:p-6">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-2xl font-bold tracking-tight">{String(data.asset.ticker)}</h2>
                  <span
                    className="rounded-full px-2.5 py-1 text-xs font-medium"
                    style={{
                      background: coverage === 'FULL' ? 'oklch(from var(--color-success) l c h / 0.15)' : 'var(--color-surface-2)',
                      color: coverage === 'FULL' ? 'var(--color-success)' : 'var(--color-text-muted)',
                    }}
                  >
                    Cobertura {coverageLabel}
                  </span>
                  <Link
                    to={`/carteira/ferramentas/comparador?add=${encodeURIComponent(String(data.asset.ticker))}`}
                    className="btn btn-secondary inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium"
                  >
                    <ChartNoAxesCombined size={13} /> Comparar ativo
                  </Link>
                </div>
                <p className="mt-1 text-sm" style={{ color: 'var(--color-text-muted)' }}>{String(data.asset.name ?? 'Nome não informado')} · Moeda de negociação: {currency}</p>
                <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs" style={{ color: 'var(--color-text-muted)' }}>
                  {catalogFields.map(([label, field, value]) => (
                    <span key={field}><span className="font-medium" style={{ color: 'var(--color-text)' }}>{label}:</span> {formatField(field, value, currency)}</span>
                  ))}
                </div>
              </div>
              <div className="shrink-0 rounded-xl p-4 sm:min-w-52 sm:text-right" style={{ background: 'var(--color-surface-2)' }}>
                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Último preço registrado</p>
                <p className="mt-1 text-2xl font-bold tabular-nums">{data.asset.last_price == null ? '—' : money(Number(data.asset.last_price), currency)}</p>
                <p className="mt-1 text-xs" style={{ color: 'var(--color-text-muted)' }}>{data.asset.last_price_updated_at ? `Referência: ${safeDate(data.asset.last_price_updated_at, true)}` : 'Data de referência indisponível'}</p>
              </div>
            </div>
            <div className="flex items-start gap-2 border-t px-5 py-3 text-xs" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}>
              <Activity size={14} className="mt-0.5 shrink-0" />
              <p>Dados informativos armazenados no sistema. Cada seção pode ter uma data de referência própria; valores e indicadores não representam recomendação de investimento.</p>
            </div>
          </section>

          <nav aria-label="Seções da análise" className="flex gap-2 overflow-x-auto pb-1">
            {aiAnalysis && <SectionLink href="#ia-analise" icon={Sparkles}>Análise IA</SectionLink>}
            <SectionLink href="#fundamentos" icon={CircleDollarSign}>Fundamentos</SectionLink>
            <SectionLink href="#historico" icon={ChartNoAxesCombined} count={data.price_history.length}>Histórico</SectionLink>
            <SectionLink href="#proventos" icon={ArrowDownToLine} count={data.dividends.length}>Proventos</SectionLink>
            <SectionLink href="#relatorios" icon={FileText} count={reports.length}>Relatórios</SectionLink>
            <SectionLink href="#noticias" icon={Newspaper} count={news.length}>Notícias</SectionLink>
            <SectionLink href="#eventos" icon={CalendarDays} count={data.corporate_events.length}>Eventos</SectionLink>
          </nav>

          {aiAnalysis && (
            <section id="ia-analise" className="scroll-mt-6 card p-5 sm:p-6 space-y-5">
              <div className="flex flex-wrap items-start justify-between gap-4 border-b pb-4" style={{ borderColor: 'var(--color-border)' }}>
                <div className="flex items-center gap-3">
                  <div
                    className="flex h-10 w-10 items-center justify-center rounded-xl"
                    style={{
                      background: 'oklch(from var(--color-primary) l c h / 0.14)',
                      color: 'var(--color-primary)',
                    }}
                  >
                    <Sparkles size={20} />
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-lg font-bold">Diagnóstico por IA e Confronto Gerencial</h2>
                      {aiAnalysis.verdict_label && (
                        <span
                          className="rounded-full px-2.5 py-0.5 text-xs font-semibold"
                          style={{
                            background: (aiAnalysis.score ?? 70) >= 75
                              ? 'oklch(from var(--color-success) l c h / 0.16)'
                              : 'var(--color-surface-2)',
                            color: (aiAnalysis.score ?? 70) >= 75 ? 'var(--color-success)' : 'var(--color-text)',
                          }}
                        >
                          {aiAnalysis.verdict_label}
                        </span>
                      )}
                    </div>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
                      Cruzamento automatizado de múltiplos, histórico de cotações, proventos e últimos relatórios CVM/B3.
                    </p>
                  </div>
                </div>
                {aiAnalysis.score != null && (
                  <div className="rounded-xl px-4 py-2 text-right" style={{ background: 'var(--color-surface-2)' }}>
                    <span className="block text-[11px]" style={{ color: 'var(--color-text-muted)' }}>Score Analítico</span>
                    <span className="text-xl font-bold tabular-nums" style={{ color: 'var(--color-primary)' }}>
                      {aiAnalysis.score}/100
                    </span>
                  </div>
                )}
              </div>

              {aiAnalysis.executive_summary && (
                <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text)' }}>
                  {aiAnalysis.executive_summary}
                </p>
              )}

              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-xl border p-4 space-y-2.5" style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface-offset)' }}>
                  <div className="flex items-center gap-2 text-xs font-semibold" style={{ color: 'var(--color-success)' }}>
                    <CheckCircle2 size={15} />
                    <span>Pontos Fortes</span>
                  </div>
                  <ul className="space-y-2 text-xs leading-relaxed" style={{ color: 'var(--color-text)' }}>
                    {(aiAnalysis.strengths ?? []).map((item, idx) => (
                      <li key={idx}>• {item}</li>
                    ))}
                  </ul>
                </div>

                <div className="rounded-xl border p-4 space-y-2.5" style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface-offset)' }}>
                  <div className="flex items-center gap-2 text-xs font-semibold" style={{ color: 'var(--color-gold)' }}>
                    <AlertTriangle size={15} />
                    <span>Pontos de Atenção</span>
                  </div>
                  <ul className="space-y-2 text-xs leading-relaxed" style={{ color: 'var(--color-text)' }}>
                    {(aiAnalysis.attention_points ?? []).map((item, idx) => (
                      <li key={idx}>• {item}</li>
                    ))}
                  </ul>
                </div>

                <div className="rounded-xl border p-4 space-y-2.5" style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface-offset)' }}>
                  <div className="flex items-center gap-2 text-xs font-semibold" style={{ color: 'var(--color-primary)' }}>
                    <FileText size={15} />
                    <span>Confronto Dados × Relatórios</span>
                  </div>
                  <ul className="space-y-2 text-xs leading-relaxed" style={{ color: 'var(--color-text)' }}>
                    {(aiAnalysis.report_confrontation ?? []).map((item, idx) => (
                      <li key={idx}>• {item}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {aiAnalysis.latest_report_referenced?.excerpt_preview && (
                <div className="rounded-xl border p-4 text-xs space-y-1.5" style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface-2)' }}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold" style={{ color: 'var(--color-text)' }}>
                      Trecho extraído do último Relatório Gerencial ({aiAnalysis.latest_report_referenced.reference_date || 'CVM/B3'})
                    </span>
                    {aiAnalysis.latest_report_referenced.url && (
                      <a
                        href={aiAnalysis.latest_report_referenced.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 font-semibold hover:underline"
                        style={{ color: 'var(--color-primary)' }}
                      >
                        Abrir PDF oficial <ExternalLink size={12} />
                      </a>
                    )}
                  </div>
                  <p className="leading-relaxed" style={{ color: 'var(--color-text-muted)' }}>
                    {aiAnalysis.latest_report_referenced.excerpt_preview}
                  </p>
                </div>
              )}
            </section>
          )}

          <section id="fundamentos" className="scroll-mt-6 space-y-4">
            <div>
              <h2 className="text-lg font-semibold">Fundamentos e indicadores</h2>
              <p className="mt-1 text-sm" style={{ color: 'var(--color-text-muted)' }}>Indicadores disponíveis para a classe deste ativo, conforme o último enriquecimento armazenado.</p>
            </div>
            {!fundamentals.length && !data.enrichment.dividend_metrics ? (
              <div className="card p-5 text-sm" style={{ color: 'var(--color-text-muted)' }}>Ainda não há fundamentos armazenados para este ativo.</div>
            ) : (
              <div className="grid gap-4 xl:grid-cols-2">
                {fundamentals.map(([key, value]) => (
                  <section key={key} className="card p-4 sm:p-5">
                    <h3 className="mb-3 font-semibold">{humanize(key)}</h3>
                    {typeof value === 'object' && value !== null && !Array.isArray(value) ? (
                      <dl className="grid gap-2 sm:grid-cols-2">
                        {Object.entries(value as DataRow).filter(([, item]) => item !== null && item !== undefined && item !== '').map(([field, fieldValue]) => (
                          <MetricCard key={field} name={field} value={fieldValue} currency={currency} />
                        ))}
                      </dl>
                    ) : (
                      <p className="text-sm">{formatField(key, value, currency)}</p>
                    )}
                  </section>
                ))}
                {data.enrichment.dividend_metrics != null && (
                  <section className="card p-4 sm:p-5">
                    <h3 className="mb-3 font-semibold">Proventos (12 meses)</h3>
                    <dl className="grid gap-2 sm:grid-cols-2">
                      {Object.entries(data.enrichment.dividend_metrics as DataRow).filter(([, item]) => item !== null && item !== undefined && item !== '').map(([field, value]) => (
                        <MetricCard key={field} name={field} value={value} currency={currency} />
                      ))}
                    </dl>
                  </section>
                )}
              </div>
            )}
            {data.enrichment.capabilities != null && (
              <section className="card p-4 sm:p-5">
                <h3 className="mb-3 font-semibold">Cobertura por tipo de dado</h3>
                <dl className="grid gap-2 sm:grid-cols-2">
                  {Object.entries(data.enrichment.capabilities as DataRow).map(([field, value]) => (
                    <MetricCard key={field} name={field} value={value} currency={currency} />
                  ))}
                </dl>
              </section>
            )}
          </section>

          <DailyPriceHistorySection rows={data.price_history} currency={currency} />

          <DividendsHistorySection rows={data.dividends} currency={currency} />

          <section id="relatorios" className="scroll-mt-6 space-y-3">
            <div>
              <h2 className="text-lg font-semibold">Relatórios gerenciais e documentos CVM/B3</h2>
              <p className="mt-1 text-sm" style={{ color: 'var(--color-text-muted)' }}>
                Relatórios gerenciais, informes mensais (Fundos.NET) e demonstrações financeiras estruturadas (ITR, DFP e FRE na B3/CVM).
              </p>
            </div>
            <div className="card p-5">
              {reports.length ? (
                <div className="space-y-3">
                  <p className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
                    Há {reports.length} relatório(s) oficial(is) disponível(is) para consulta direta:
                  </p>
                  <div className="grid gap-3 md:grid-cols-2">
                    {reports.map((rep, idx) => (
                      <div
                        key={rep.id || idx}
                        className="rounded-xl border p-3.5 flex items-start justify-between gap-3"
                        style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface-offset)' }}
                      >
                        <div className="min-w-0 space-y-1">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <span className="text-sm font-semibold truncate" style={{ color: 'var(--color-text)' }}>
                              {rep.title || rep.category || 'Documento Oficial'}
                            </span>
                            {rep.is_management_report && (
                              <span
                                className="rounded-full px-2 py-0.5 text-[10px] font-semibold"
                                style={{
                                  background: 'oklch(from var(--color-primary) l c h / 0.14)',
                                  color: 'var(--color-primary)',
                                }}
                              >
                                Destaque Analítico
                              </span>
                            )}
                          </div>
                          <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                            {rep.category && rep.category !== rep.title ? `${rep.category} · ` : ''}
                            Ref.: {safeDate(rep.reference_date)} · Entrega: {safeDate(rep.delivery_date)}
                          </p>
                          {rep.source && (
                            <p className="text-[11px]" style={{ color: 'var(--color-text-faint)' }}>
                              Fonte: {rep.source}
                            </p>
                          )}
                        </div>
                        {rep.url && (
                          <a
                            href={rep.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-secondary shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold"
                          >
                            <span>Abrir</span>
                            <ExternalLink size={12} />
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex items-start gap-3">
                  <div className="rounded-lg p-2" style={{ background: 'var(--color-surface-2)', color: 'var(--color-text-muted)' }}>
                    <FileText size={18} />
                  </div>
                  <div>
                    <p className="font-medium">Nenhum relatório vinculado</p>
                    <p className="mt-1 text-sm" style={{ color: 'var(--color-text-muted)' }}>O sistema ainda não possui relatórios gerenciais anexados a este ativo.</p>
                  </div>
                </div>
              )}
            </div>
          </section>

          <section id="noticias" className="scroll-mt-6 space-y-3">
            <div>
              <h2 className="text-lg font-semibold">Notícias de mercado sobre o ativo</h2>
              <p className="mt-1 text-sm" style={{ color: 'var(--color-text-muted)' }}>
                Acompanhamento de notícias externas recentes envolvendo o ticker e a companhia ou fundo.
              </p>
            </div>
            <div className="card p-5">
              {news.length ? (
                <div className="grid gap-3 md:grid-cols-2">
                  {news.map((item, idx) => (
                    <a
                      key={idx}
                      href={item.url || '#'}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="rounded-xl border p-3.5 flex flex-col justify-between gap-2 transition-colors hover:bg-[var(--color-surface-2)]"
                      style={{ borderColor: 'var(--color-border)', background: 'var(--color-surface-offset)' }}
                    >
                      <div className="space-y-1">
                        <p className="text-sm font-semibold leading-snug" style={{ color: 'var(--color-text)' }}>
                          {item.title}
                        </p>
                        {item.summary && (
                          <p className="text-xs line-clamp-2" style={{ color: 'var(--color-text-muted)' }}>
                            {item.summary}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center justify-between gap-2 pt-1 text-[11px]" style={{ color: 'var(--color-text-faint)' }}>
                        <span>{item.source || 'Noticiário'} · {safeDate(item.published_at)}</span>
                        <span className="inline-flex items-center gap-1 font-medium" style={{ color: 'var(--color-primary)' }}>
                          Ler matéria <ExternalLink size={11} />
                        </span>
                      </div>
                    </a>
                  ))}
                </div>
              ) : (
                <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                  Nenhuma notícia externa recente localizada para este ativo no momento.
                </p>
              )}
            </div>
          </section>

          <section id="eventos" className="scroll-mt-6 space-y-3">
            <div>
              <h2 className="text-lg font-semibold">Eventos corporativos</h2>
              <p className="mt-1 text-sm" style={{ color: 'var(--color-text-muted)' }}>Eventos gerais do ativo que não estão vinculados a uma carteira específica.</p>
            </div>
            <DataTable title="Eventos registrados" rows={data.corporate_events} currency={currency} empty="Não há eventos corporativos gerais armazenados para este ativo." />
          </section>
        </>
      )}
    </div>
  )
}
