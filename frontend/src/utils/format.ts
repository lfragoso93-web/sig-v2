export function formatBRL(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style:    'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
  }).format(value)
}

export function formatPercent(value: number, decimals = 2): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('pt-BR').format(new Date(iso + 'T00:00:00'))
}

export function formatDateShort(iso: string): string {
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString('pt-BR', { month: 'short', year: '2-digit' })
}

/** Retorna classe CSS para badge de tipo de ativo */
export function assetBadgeClass(type: string): string {
  const t = type.toLowerCase()
  if (t.includes('fii'))          return 'badge-fii'
  if (t.includes('etf'))          return 'badge-etf'
  if (t.includes('tesouro'))      return 'badge-tesouro'
  if (t.includes('stock'))        return 'badge-stock'
  if (t.includes('cripto'))       return 'badge-cripto'
  if (t.includes('renda'))        return 'badge-rendafixa'
  return 'badge-acao'
}

export function formatLargeNumber(value: number): string {
  if (Math.abs(value) >= 1_000_000)
    return `R$ ${(value / 1_000_000).toFixed(1)}M`
  if (Math.abs(value) >= 1_000)
    return `R$ ${(value / 1_000).toFixed(1)}k`
  return formatBRL(value)
}
