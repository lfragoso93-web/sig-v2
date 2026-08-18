import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const sourcePath = (relativePath: string) => resolve(process.cwd(), relativePath)

describe('canonical application logo', () => {
  it('keeps the unused SigLogo implementation absent', () => {
    expect(existsSync(sourcePath('src/components/ui/SigLogo.tsx'))).toBe(false)
  })

  it.each([
    'src/components/layout/Topbar.tsx',
    'src/components/layout/AuthLayout.tsx',
  ])('keeps LogoSGI mounted in %s', (relativePath) => {
    const source = readFileSync(sourcePath(relativePath), 'utf8')
    expect(source).toContain("@/components/ui/LogoSGI")
    expect(source).toContain('<LogoSGI')
    expect(source).not.toContain('SigLogo')
  })
})
