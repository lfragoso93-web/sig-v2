import numeral from 'numeral'

// ── Moeda ────────────────────────────────────────────────────────────────────
export function formatCurrency(value: number): string {
  return numeral(value).format('R$ 0,0.00')
}

export function formatUSD(value: number): string {
  return numeral(value).format('$ 0,0.00')
}

// ── Percentual ───────────────────────────────────────────────────────────────
export function formatPercent(value: number): string {
  return numeral(value / 100).format('0.00%')
}

/** Alias usado em vários componentes */
export const formatPct = formatPercent

// ── Quantidade ───────────────────────────────────────────────────────────────
export function formatQuantity(value: number): string {
  return numeral(value).format('0,0.####')
}

// ── Data ─────────────────────────────────────────────────────────────────────
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

// ── Classe de cor por sinal ───────────────────────────────────────────────────
export function signClass(value: number): string {
  if (value > 0) return 'text-green-500'
  if (value < 0) return 'text-red-500'
  return 'text-gray-400'
}
