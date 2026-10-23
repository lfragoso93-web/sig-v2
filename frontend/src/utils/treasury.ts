/**
 * Resolve o nome comercial oficial de títulos do Tesouro Direto para exibição na UI,
 * sem alterar o ticker/símbolo canônico interno e sem depender de provider em render.
 *
 * Exemplos:
 *   TESOURO-SELIC-01032031                       → Tesouro Selic 2031
 *   TESOURO-IPCA-MAIS-01032035                   → Tesouro IPCA+ 2035
 *   TESOURO-IPCA-MAIS-COM-JUROS-SEMESTRAIS-...   → Tesouro IPCA+ c/ Juros Semestrais 2035
 *   TESOURO-PREFIXADO-01012026                   → Tesouro Prefixado 2026
 *   TESOURO-PREFIXADO-COM-JUROS-SEMESTRAIS-...   → Tesouro Prefixado c/ Juros Semestrais 2026
 *   TESOURO-RENDA-PLUS-01032065                  → Tesouro RendA+ Aposentadoria Extra 2065
 *   Tesouro RENDA MAIS 2065                      → Tesouro RendA+ Aposentadoria Extra 2065
 *   TESOURO-EDUCA-MAIS-01032045                  → Tesouro Educa+ 2045
 */
export function formatTreasuryName(ticker: string, canonicalLabel?: string | null): string {
  const source = (canonicalLabel && canonicalLabel.trim().length > 0 ? canonicalLabel : ticker).trim()
  const upperSource = source.toUpperCase()
  const upperTicker = ticker.trim().toUpperCase()

  // Caso 1: Label comercial já formatado para Educa+ (preserva o ano do produto sem inferir do vencimento)
  const educaLabelMatch = source.match(/^Tesouro\s+Educa\+?\s+(\d{4})$/i)
  if (educaLabelMatch) {
    return `Tesouro Educa+ ${educaLabelMatch[1]}`
  }

  // Caso 2: Variações técnicas/comerciais de RendA+ (ex.: "Tesouro RENDA MAIS 2065" ou "Tesouro Renda+ 2065")
  const rendaSpaceMatch = source.match(
    /^Tesouro\s+Rend[aA]\s*(?:\+|Mais|Plus)(?:\s+Aposentadoria\s+Extra)?\s+(\d{4})$/i,
  )
  if (rendaSpaceMatch) {
    return `Tesouro RendA+ Aposentadoria Extra ${rendaSpaceMatch[1]}`
  }

  if (!upperTicker.startsWith('TESOURO-') && !upperSource.startsWith('TESOURO ')) {
    return source
  }

  if (upperTicker.startsWith('TESOURO-')) {
    const s = upperTicker.replace(/^TESOURO-/, '')
    const dateMatch = s.match(/(\d{8}|\d{4})$/)
    const rawDate = dateMatch ? dateMatch[1] : ''
    const year = rawDate.length === 8 ? rawDate.slice(4) : rawDate
    const typeRaw = s.replace(/[-_]?(\d{8}|\d{4})$/, '')

    const TYPE_MAP: Record<string, string> = {
      'SELIC': 'Selic',
      'IPCA-MAIS': 'IPCA+',
      'IPCA-MAIS-COM-JUROS-SEMESTRAIS': 'IPCA+ c/ Juros Semestrais',
      'PREFIXADO': 'Prefixado',
      'PREFIXADO-COM-JUROS-SEMESTRAIS': 'Prefixado c/ Juros Semestrais',
      'RENDA-PLUS': 'RendA+ Aposentadoria Extra',
      'RENDA-MAIS': 'RendA+ Aposentadoria Extra',
      'RENDA-MAIS-APOSENTADORIA-EXTRA': 'RendA+ Aposentadoria Extra',
      'EDUCA-MAIS': 'Educa+',
    }

    const friendlyType = TYPE_MAP[typeRaw] ?? typeRaw.replace(/-/g, ' ')
    return year ? `Tesouro ${friendlyType} ${year}` : `Tesouro ${friendlyType}`
  }

  return source
}
