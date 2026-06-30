import numeral from 'numeral'

// -- Moeda -------------------------------------------------------------------
const brFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const brFormatterShort = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  notation: 'compact',
  minimumFractionDigits: 0,
  maximumFractionDigits: 1,
})

const usdFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

/** Converte qualquer valor para número seguro (0 se null/undefined/NaN/Infinity) */
function safeFinite(v: unknown): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

export function formatCurrency(value: number | null | undefined, short?: boolean): string {
  const n = safeFinite(value)
  return short ? brFormatterShort.format(n) : brFormatter.format(n)
}

/** Alias BRL -- usado em PositionsTable e outros componentes */
export const formatBRL = formatCurrency

/** Formata valor em USD com simbolo correto: US$ 1,234.56 */
export function formatUSD(value: number | null | undefined): string {
  return usdFormatter.format(safeFinite(value))
}

/**
 * Escolhe o formatador correto conforme a moeda do ativo.
 * Ativos USD (STOCK, ETF_INTERNACIONAL) exibem precos unitarios em USD.
 * Todos os demais usam BRL.
 */
export function fmtMoney(value: number | null | undefined, currency?: string | null): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '--'
  if (currency === 'USD') return formatUSD(value)
  return formatBRL(value)
}

// -- Percentual --------------------------------------------------------------
/**
 * Formata um número como percentual (ex: 12.5 → "12,50%").
 * Guard defensivo: null/undefined/NaN/Infinity → "0,00%".
 * Evita o crash "Cannot read properties of undefined (reading 'toFixed')"
 * que ocorre quando numeral recebe NaN (resultado de undefined / 100).
 */
export function formatPercent(value: number | null | undefined): string {
  const n = safeFinite(value)
  return numeral(n / 100).format('0.00%')
}

/** Alias usado em varios componentes */
export const formatPct = formatPercent

// -- Quantidade --------------------------------------------------------------
export function formatQuantity(value: number | null | undefined): string {
  return numeral(safeFinite(value)).format('0,0.####')
}

// -- Data --------------------------------------------------------------------
export function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleDateString('pt-BR')
}

export function formatDateShort(dateStr: string): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleDateString('pt-BR', { month: 'short', year: '2-digit' })
}

// -- Classe de cor por sinal -------------------------------------------------
const numFmt = numeral
void numFmt
export function signClass(value: number | null | undefined): string {
  const n = safeFinite(value)
  if (n > 0) return 'text-green-500'
  if (n < 0) return 'text-red-500'
  return 'text-gray-400'
}

// -- Badge por tipo de ativo -------------------------------------------------
export function assetBadgeClass(assetType: string | null | undefined): string {
  // Guarda ANTES de qualquer acesso ao valor — evita TypeError: Cannot read
  // properties of undefined (reading 'toUpperCase') quando asset_type chega
  // null/undefined do backend.
  if (!assetType) return 'badge-default'
  const map: Record<string, string> = {
    'ACAO':              'badge-acao',
    'ACAO_NACIONAL':     'badge-acao',
    'FII':               'badge-fii',
    'ETF':               'badge-etf',
    'ETF_NACIONAL':      'badge-etf',
    'ETF_INT':           'badge-etf-int',
    'ETF_INTERNACIONAL': 'badge-etf-int',
    'TESOURO':           'badge-tesouro',
    'TESOURO_DIRETO':    'badge-tesouro',
    'STOCK':             'badge-stock',
    'STOCKS':            'badge-stock',
    'CRIPTO':            'badge-cripto',
    'CRIPTOMOEDA':       'badge-cripto',
    'RENDA_FIXA':        'badge-renda-fixa',
  }
  return map[assetType.toUpperCase()] ?? 'badge-default'
}
