import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const sourcePath = (relativePath: string) => resolve(process.cwd(), relativePath)

describe('legacy mutation modals', () => {
  it('keeps duplicate transaction and manual-dividend surfaces absent', () => {
    expect(existsSync(sourcePath('src/components/transactions/ModalNovaTransacao.tsx'))).toBe(false)
    expect(existsSync(sourcePath('src/components/transactions/TransactionForm.tsx'))).toBe(false)
    expect(existsSync(sourcePath('src/components/dividends/ModalNovoProvento.tsx'))).toBe(false)
  })

  it('preserves the canonical transaction modal and its mutation hooks', () => {
    const modal = readFileSync(sourcePath('src/components/modals/AddTransactionModal.tsx'), 'utf8')
    expect(modal).toContain('useCreateTransaction')
    expect(modal).toContain('useUpdateTransaction')
    expect(readFileSync(sourcePath('src/components/layout/AppLayout.tsx'), 'utf8')).toContain(
      '<AddTransactionModal onClose={closeTransactionModal} />',
    )
  })

  it('keeps only read hooks in the dividend hook module', () => {
    const source = readFileSync(sourcePath('src/hooks/useDividends.ts'), 'utf8')
    expect(source).not.toContain('useCreateDividend')
    expect(source).not.toContain("api.post<Dividend>('/dividends'")
    expect(source).not.toContain('useMutation')
  })
})
