import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

import {
  LEGACY_PORTFOLIO_ROUTE_REDIRECTS,
  PORTFOLIO_ROUTES,
} from './portfolioRoutes'

const mainSource = readFileSync(resolve(process.cwd(), 'src/main.tsx'), 'utf8')

describe('portfolio route hierarchy', () => {
  it('keeps IRPF and goals under the selected portfolio context', () => {
    expect(PORTFOLIO_ROUTES.irpf).toBe('/carteira/irpf')
    expect(PORTFOLIO_ROUTES.goals).toBe('/carteira/metas')
  })

  it('preserves legacy URLs as redirects to canonical portfolio routes', () => {
    expect(LEGACY_PORTFOLIO_ROUTE_REDIRECTS['/irpf']).toBe(PORTFOLIO_ROUTES.irpf)
    expect(LEGACY_PORTFOLIO_ROUTE_REDIRECTS['/metas']).toBe(PORTFOLIO_ROUTES.goals)
  })

  it('keeps compatibility paths as replace-only redirects in the application entry', () => {
    expect(mainSource).toContain(
      "<Navigate to={LEGACY_PORTFOLIO_ROUTE_REDIRECTS['/metas']} replace />",
    )
    expect(mainSource).toContain(
      "<Navigate to={LEGACY_PORTFOLIO_ROUTE_REDIRECTS['/irpf']} replace />",
    )
    expect(mainSource).not.toContain("path: '/metas',         element: <MetasPage")
    expect(mainSource).not.toContain("path: '/irpf',          element: <IRPFPage")
  })
})
