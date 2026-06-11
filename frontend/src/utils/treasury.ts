/**
 * Converte o slug da BRAPI em nome amigável para exibição.
 *
 * Exemplos:
 *   TESOURO-SELIC-01032031                       → Tesouro Selic 2031
 *   TESOURO-IPCA-MAIS-01032035                   → Tesouro IPCA+ 2035
 *   TESOURO-IPCA-MAIS-COM-JUROS-SEMESTRAIS-...   → Tesouro IPCA+ c/ Juros Semestrais 2035
 *   TESOURO-PREFIXADO-01012026                   → Tesouro Prefixado 2026
 *   TESOURO-PREFIXADO-COM-JUROS-SEMESTRAIS-...   → Tesouro Prefixado c/ Juros Semestrais 2026
 *   TESOURO-RENDA-PLUS-01032065                  → Tesouro Renda+ 2065
 *   TESOURO-EDUCA-MAIS-01032045                  → Tesouro Educa+ 2045
 *
 * Para tickers que não começam com TESOURO-, retorna o ticker original sem alteração.
 */
export function formatTreasuryName(ticker: string): string {
  const upper = ticker.toUpperCase()
  if (!upper.startsWith('TESOURO-')) return ticker

  // Remove o prefixo TESOURO-
  const s = upper.replace(/^TESOURO-/, '')

  // Extrai o ano dos últimos 8 dígitos (DDMMYYYY)
  const dateMatch = s.match(/(\d{8})$/)
  const year = dateMatch ? dateMatch[1].slice(4) : ''

  // Remove o trecho de data para processar o tipo
  const typeRaw = s.replace(/[-_]?\d{8}$/, '')

  const TYPE_MAP: Record<string, string> = {
    'SELIC':                                   'Selic',
    'IPCA-MAIS':                               'IPCA+',
    'IPCA-MAIS-COM-JUROS-SEMESTRAIS':          'IPCA+ c/ Juros Semestrais',
    'PREFIXADO':                               'Prefixado',
    'PREFIXADO-COM-JUROS-SEMESTRAIS':          'Prefixado c/ Juros Semestrais',
    'RENDA-PLUS':                              'Renda+',
    'EDUCA-MAIS':                              'Educa+',
  }

  const friendlyType = TYPE_MAP[typeRaw] ?? typeRaw.replace(/-/g, ' ')

  return year ? `Tesouro ${friendlyType} ${year}` : `Tesouro ${friendlyType}`
}
