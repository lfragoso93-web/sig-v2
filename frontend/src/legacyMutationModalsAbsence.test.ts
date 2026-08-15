import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const sourcePath = (relativePath: string) => resolve(process.cwd(), relativePath)

describe('legacy mutation modals', () => {
  it('keeps the duplicate transaction and manual-dividend modals absent', () => {
    expect(existsSync(sourcePath('src/components/transactions/ModalNovaTransacao.tsx'))).toBe(false)
    expect(existsSync(sourcePath('src/components/dividends/ModalNovoProvento.tsx'))).toBe(false)
  })

  it('keeps only read hooks in the dividend hook module', () => {
    const source = readFileSync(sourcePath('src/hooks/useDividends.ts'), 'utf8')
    expect(source).not.toContain('useCreateDividend')
    expect(source).not.toContain("api.post<Dividend>('/dividends'")
    expect(source).not.toContain('useMutation')
  })
})
