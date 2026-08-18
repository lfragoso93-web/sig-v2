import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const sourcePath = (relativePath: string) => resolve(process.cwd(), relativePath)

describe('orphan dividend views', () => {
  it('keeps legacy Dividend chart and table absent', () => {
    expect(existsSync(sourcePath('src/components/dividends/DividendChart.tsx'))).toBe(false)
    expect(existsSync(sourcePath('src/components/dividends/DividendTable.tsx'))).toBe(false)
  })

  it('preserves the canonical Proventos page components', () => {
    const page = readFileSync(sourcePath('src/pages/ProventosPage.tsx'), 'utf8')
    expect(page).toContain("@/components/charts/ProventosDonutChart")
    expect(page).toContain("@/components/proventos/ProventosHistoricoTable")
    expect(page).toContain("@/components/proventos/MeusProventosTable")
    expect(page).not.toContain('DividendChart')
    expect(page).not.toContain('DividendTable')
  })
})
