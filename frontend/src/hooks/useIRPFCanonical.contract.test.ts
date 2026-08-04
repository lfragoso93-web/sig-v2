import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const source = readFileSync(
  fileURLToPath(new URL('./useIRPF.ts', import.meta.url)),
  'utf8',
)

describe('IRPF canonical query contract', () => {
  it('uses the canonical annual endpoint and a dedicated cache key', () => {
    expect(source).toContain("['irpf-canonical-annual-assessment', portfolioId, year]")
    expect(source).toContain(
      '`/portfolios/${portfolioId}/irpf/${year}/canonical`',
    )
  })

  it('does not replace the legacy complementary report query', () => {
    expect(source).toContain("['irpf-report', portfolioId, year, refresh]")
    expect(source).toContain('useIRPFCanonicalAnnualAssessment')
    expect(source).toContain('useIRPFReport')
  })
})
