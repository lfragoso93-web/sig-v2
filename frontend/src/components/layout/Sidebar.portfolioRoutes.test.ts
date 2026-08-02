import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const sidebarPath = resolve(process.cwd(), 'src/components/layout/Sidebar.tsx')
const sidebarSource = readFileSync(sidebarPath, 'utf8')

describe('Sidebar portfolio route hierarchy', () => {
  it('links IRPF and goals directly under /carteira', () => {
    expect(sidebarSource).toContain("to: '/carteira/metas'")
    expect(sidebarSource).toContain("to: '/carteira/irpf'")
  })

  it('does not navigate through legacy top-level URLs', () => {
    expect(sidebarSource).not.toContain("to: '/metas'")
    expect(sidebarSource).not.toContain("to: '/irpf'")
  })
})
