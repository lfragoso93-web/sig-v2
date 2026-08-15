import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const sourcePath = (relativePath: string) => resolve(process.cwd(), relativePath)

describe('orphan dashboard components', () => {
  it.each([
    'src/components/dashboard/AllocationChart.tsx',
    'src/components/dashboard/ModalNovaCarteira.tsx',
    'src/components/charts/ConcentrationTreemap.tsx',
  ])('keeps %s absent', (relativePath) => {
    expect(existsSync(sourcePath(relativePath))).toBe(false)
  })

  it('preserves the active allocation and portfolio creation surfaces', () => {
    expect(readFileSync(sourcePath('src/components/charts/AssetDonutChart.tsx'), 'utf8')).toContain('ResponsiveContainer')
    expect(readFileSync(sourcePath('src/components/configuracoes/DistribuicaoCarteira.tsx'), 'utf8')).toContain('useClassTargets')
    expect(readFileSync(sourcePath('src/components/layout/Sidebar.tsx'), 'utf8')).toContain('useCreatePortfolio')
  })
})
