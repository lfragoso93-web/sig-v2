import numeral from 'numeral'

// ── Moeda ──────────────────────────────────────────────────────────────────────────────
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

export function formatCurrency(value: number, short?: boolean): string {
  if (!Number.isFinite(value)) return brFormatter.format(0)
  return short ? brFormatterShort.format(value) : brFormatter.format(value)
}

/** Alias BRL — usado em PositionsTable e outros componentes */
export const formatBRL = formatCurrency

export function formatUSD(value: number): string {
  return numeral(value).format('$ 0,0.00')
}

// ── Percentual ────────────────────────────────────────────────────────────────
export function formatPercent(value: number): string {
  return numeral(value / 100).format('0.00%')
}

/** Alias usado em vários componentes */
export const formatPct = formatPercent

// ── Quantidade ──────────────────────────────────────────────────────────────────────
export function formatQuantity(value: number): string {
  return numeral(value).format('0,0.####')
}

// ── Data ────────────────────────────────────────────────────────────────────────────────
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

// ── Classe de cor por sinal ───────────────────────────────────────────────────────────────
export function signClass(value: number): string {
  if (value > 0) return 'text-green-500'
  if (value < 0) return 'text-red-500'
  return 'text-gray-400'
}

// ── Badge por tipo de ativo ─────────────────────────────────────────────────────────────
export function assetBadgeClass(assetType: string): string {
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
