import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const source = readFileSync(
  resolve(process.cwd(), 'src/pages/IRPFPage.tsx'),
  'utf8',
)

describe('IRPF asset presentation', () => {
  it('prefers the persisted display name and keeps ticker visible', () => {
    expect(source).toContain('{b.nome || b.ticker}')
    expect(source).toContain('b.nome !== b.ticker')
    expect(source).toContain('{b.ticker}')
  })
})
