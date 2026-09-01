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

  it('blocks partial import when validation reports warnings, skipped rows, or errors', () => {
    expect(source).toContain('result.error_count > 0')
    expect(source).toContain('result.skipped_count > 0')
    expect(source).toContain('result.global_errors.length > 0')
    expect(source).toContain('Corrija os erros ou avisos do CSV antes de confirmar. Nenhuma linha será importada parcialmente.')
  })

  it('refreshes portfolio views only after a successful import with persisted rows', () => {
    const successGate = source.indexOf('if (importResult.success && importResult.imported_count > 0)')
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
