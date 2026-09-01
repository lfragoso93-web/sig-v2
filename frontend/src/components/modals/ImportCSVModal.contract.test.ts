import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const sourcePath = join(process.cwd(), 'src/components/modals/ImportCSVModal.tsx')

describe('ImportCSVModal CSV contract', () => {
  const source = readFileSync(sourcePath, 'utf-8')

  it('validates synthetic CSV content before allowing the real import call', () => {
    const validateFileIndex = source.indexOf('const validateFile = async')
    const importIndex = source.indexOf('const handleImport = async')

    expect(validateFileIndex).toBeGreaterThanOrEqual(0)
    expect(importIndex).toBeGreaterThan(validateFileIndex)
    expect(source).toContain("params: { dry_run: true }")
    expect(source).toContain("params: { dry_run: false }")
    expect(source).toContain('disabled={isLoading || !result || hasBlockingErrors}')
  })

  it('refreshes portfolio views only after a successful import response', () => {
    const successGate = source.indexOf('if (importResult.success)')
    const refreshCall = source.indexOf('invalidateImportedData()')
    const successCallback = source.indexOf('onSuccess?.()')

    expect(successGate).toBeGreaterThanOrEqual(0)
    expect(refreshCall).toBeGreaterThan(successGate)
    expect(successCallback).toBeGreaterThan(refreshCall)
    expect(source).toContain("'portfolio-summary'")
    expect(source).toContain("'positions'")
    expect(source).toContain("'rentabilidade-kpis'")
    expect(source).toContain("'rentabilidade-classes'")
  })
})
