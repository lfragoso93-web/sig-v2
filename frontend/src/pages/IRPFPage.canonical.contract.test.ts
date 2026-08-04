import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const source = readFileSync(
  fileURLToPath(new URL('./IRPFPage.tsx', import.meta.url)),
  'utf8',
)

describe('IRPF page canonical summary boundary', () => {
  it('renders primary tax KPIs from the canonical assessment', () => {
    expect(source).toContain('useIRPFCanonicalAnnualAssessment')
    expect(source).toContain('total_gross_tax_due_brl')
    expect(source).toContain('total_withholding_brl')
    expect(source).toContain('total_payment_due_brl')
    expect(source).toContain('closing_day_trade_loss_carryforward_brl')
  })

  it('keeps complementary tabs and downloads on the legacy report temporarily', () => {
    expect(source).toContain('useIRPFReport')
    expect(source).toContain('/pdf`')
    expect(source).toContain('/csv`')
    expect(source).toContain('report?.bens_direitos')
    expect(source).toContain('report?.rendimentos_isentos')
  })
})
