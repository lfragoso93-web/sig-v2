import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

const sidebarPath = fileURLToPath(new URL('./Sidebar.tsx', import.meta.url))
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
