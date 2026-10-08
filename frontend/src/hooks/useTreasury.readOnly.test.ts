import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const read = (relativePath: string) =>
  readFileSync(resolve(process.cwd(), relativePath), 'utf8')

describe('Treasury read-only boundary', () => {
  it('keeps the Treasury hook limited to the persisted GET endpoint', () => {
    const source = read('src/hooks/useTreasury.ts')

    expect(source).toContain('api.get<TreasuryItem[]>')
    expect(source).not.toMatch(/api\.(post|patch|delete)/)
    expect(source).not.toMatch(/\b(create|update|remove)\b/)
  })

  it('does not expose a destructive Treasury action in the page', () => {
    const source = read('src/pages/patrimonio/TesouroDiretoPage.tsx')

    expect(source).not.toContain('Excluir investimento')
    expect(source).not.toContain('handleDelete')
    expect(source).not.toContain('setDeleteItem')
  })

  it('prefers the persisted commercial name without replacing the ticker identity', () => {
    const hook = read('src/hooks/useTreasury.ts')
    const page = read('src/pages/patrimonio/TesouroDiretoPage.tsx')

    expect(hook).toContain('commercial_name?: string | null')
    expect(page).toContain('item.commercial_name || item.brapi_name')
    expect(page).toContain('item.brapi_symbol || item.ticker || item.brapi_name')
  })
})
