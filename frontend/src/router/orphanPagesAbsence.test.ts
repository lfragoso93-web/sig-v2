import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const sourcePath = (relativePath: string) => resolve(process.cwd(), relativePath)

describe('orphan pages', () => {
  it('keeps unmounted Assets and duplicate Lancamentos pages absent', () => {
    expect(existsSync(sourcePath('src/pages/AssetsPage.tsx'))).toBe(false)
    expect(existsSync(sourcePath('src/pages/LancamentosPage.tsx'))).toBe(false)
  })

  it('keeps the canonical transactions page routed', () => {
    const main = readFileSync(sourcePath('src/main.tsx'), 'utf8')
    expect(main).toMatch(/import\(['\"]@\/pages\/Transacoes['\"]\)/)
    expect(main).toMatch(/path:\s*'transacoes'/)
    expect(main).not.toContain('AssetsPage')
    expect(main).not.toContain('LancamentosPage')
  })
})
