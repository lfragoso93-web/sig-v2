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
})
