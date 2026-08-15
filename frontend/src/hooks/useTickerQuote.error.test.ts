import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const source = readFileSync(resolve(process.cwd(), 'src/hooks/useTickerQuote.ts'), 'utf8')

describe('useTickerQuote error contract', () => {
  it('distinguishes a missing asset from provider or transport failure', () => {
    expect(source).toContain('catch (error: unknown)')
    expect(source).toContain("status === 404")
    expect(source).toContain('Ativo não encontrado no catálogo.')
    expect(source).toContain('Não foi possível consultar a cotação. Tente novamente.')
  })

  it('does not expose a provider name or silently clear non-404 errors', () => {
    expect(source).not.toContain('BRAPI')
    expect(source).not.toContain('else {\n          setError(null)')
  })
})
