import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const sourcePath = (relativePath: string) => resolve(process.cwd(), relativePath)

const removedServices = [
  'transactionService.ts',
  'authService.ts',
  'fxService.ts',
  'classTargetsService.ts',
  'performanceService.ts',
  'goalsService.ts',
  'assetService.ts',
]

describe('orphan HTTP services', () => {
  it.each(removedServices)('keeps services/%s absent', (fileName) => {
    expect(existsSync(sourcePath(`src/services/${fileName}`))).toBe(false)
  })

  it('preserves the canonical HTTP entry points', () => {
    expect(readFileSync(sourcePath('src/contexts/AuthContext.tsx'), 'utf8')).toContain("'/auth/login'")
    expect(readFileSync(sourcePath('src/hooks/useTransactions.ts'), 'utf8')).toContain('/transactions')
    expect(readFileSync(sourcePath('src/hooks/useClassTargets.ts'), 'utf8')).toContain('/class-targets/')
    expect(readFileSync(sourcePath('src/hooks/useGoals.ts'), 'utf8')).toContain('/goals')
    expect(readFileSync(sourcePath('src/hooks/useEvolution.ts'), 'utf8')).toContain('/performance/')
  })

  it('keeps hooks orphaned with the asset catalog page absent', () => {
    expect(existsSync(sourcePath('src/hooks/useAssets.ts'))).toBe(false)
    expect(existsSync(sourcePath('src/hooks/useFxRate.ts'))).toBe(false)
  })
})
