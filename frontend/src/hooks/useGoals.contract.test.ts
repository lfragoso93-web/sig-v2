import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

describe('useGoals API contract', () => {
  it('updates goals using the backend PUT contract', () => {
    const source = readFileSync('src/hooks/useGoals.ts', 'utf8')

    expect(source).toContain('api.put<Goal>(`/portfolios/${portfolioId}/goals/${id}`')
    expect(source).not.toContain('api.patch<Goal>(`/portfolios/${portfolioId}/goals/${id}`')
  })
})
