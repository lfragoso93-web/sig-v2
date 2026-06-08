// ─ Moeda ───────────────────────────────────────────────────────────────────────
export function formatBRL(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

export function formatUSD(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

// ─ Percentual ───────────────────────────────────────────────────────────────
export function formatPct(value: number, decimals = 2): string {
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(decimals)}%`
}

// ─ Data ────────────────────────────────────────────────────────────────────────
export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(iso))
}

export function formatDateShort(iso: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: 'short',
  }).format(new Date(iso))
}

// ─ Número compacto ────────────────────────────────────────────────────────────
export function formatCompact(value: number): string {
  if (value >= 1_000_000) return `R$ ${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000)     return `R$ ${(value / 1_000).toFixed(1)}K`
  return formatBRL(value)
}

// ─ Badge class por tipo de ativo ───────────────────────────────────────────
const BADGE_MAP: Record<string, string> = {
  'acao nacional':     'acao',
  'fii':               'fii',
  'etf nacional':      'etf',
  'tesouro direto':    'tesouro',
  'stock':             'stock',
  'etf internacional': 'etf',
  'criptomoeda':       'cripto',
  'renda fixa':        'renda-fixa',
}

export function assetBadgeClass(type: string): string {
  return BADGE_MAP[type.toLowerCase()] ?? 'acao'
}
