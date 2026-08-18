import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const read = (relativePath: string) => readFileSync(resolve(process.cwd(), relativePath), 'utf8')

describe('market lookup error contracts', () => {
  it.each([
    ['src/hooks/useTesouroSearch.ts', 'Não foi possível consultar os títulos. Tente novamente.'],
    ['src/hooks/useTreasuryPrice.ts', 'Não foi possível consultar o preço do título. Informe-o manualmente.'],
    ['src/hooks/useTickerSuggest.ts', 'Não foi possível consultar o catálogo de ativos. Tente novamente.'],
  ])('returns an explicit error from %s', (path, message) => {
    const source = read(path)

    expect(source).toContain('const [error,')
    expect(source).toContain(`setError('${message}')`)
    expect(source).toContain('return {')
    expect(source).toContain('error }')
  })

  it('renders one provider-neutral lookup error in the transaction modal', () => {
    const source = read('src/components/modals/AddTransactionModal.tsx')

    expect(source).toContain('const lookupError = quoteError ?? tdSearchError ?? rvSearchError ?? tdPriceError')
    expect(source).toContain('lookupError && !anyLoading')
    expect(source).toContain('role="alert"')
  })
})
