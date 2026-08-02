import { describe, expect, it } from 'vitest'

import {
  LEGACY_PORTFOLIO_ROUTE_REDIRECTS,
  PORTFOLIO_ROUTES,
} from './portfolioRoutes'

describe('portfolio route hierarchy', () => {
  it('keeps IRPF and goals under the selected portfolio context', () => {
    expect(PORTFOLIO_ROUTES.irpf).toBe('/carteira/irpf')
    expect(PORTFOLIO_ROUTES.goals).toBe('/carteira/metas')
  })

  it('preserves legacy URLs as redirects to canonical portfolio routes', () => {
    expect(LEGACY_PORTFOLIO_ROUTE_REDIRECTS['/irpf']).toBe(PORTFOLIO_ROUTES.irpf)
    expect(LEGACY_PORTFOLIO_ROUTE_REDIRECTS['/metas']).toBe(PORTFOLIO_ROUTES.goals)
  })
})
